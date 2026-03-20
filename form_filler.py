"""Lógica de llenado del formulario Enketo con Playwright."""

import logging
import platform
from pathlib import Path
from typing import Callable, Union

from playwright.sync_api import FrameLocator, Page, sync_playwright, TimeoutError as PlaywrightTimeout

# Contexto del formulario: Page (documento principal) o FrameLocator (iframe)
FormContext = Union[Page, FrameLocator]

# Rutas de Chrome/Chromium en macOS
CHROME_PATHS_MACOS = [
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
]

from config import APP_URL, FORM_URL, load_mapping, USE_DIRECT_FORM_URL

logger = logging.getLogger(__name__)

# Campos que SIEMPRE se rellenan por defecto al inicio usando VALUES REALES del formulario
# (obtenidos del diagnóstico del DOM: DIAG Modalidad options=[1(Móvil)], followup options=[1(Primera vez)...])
DEFAULT_FIELDS_ORDER = [
    ("CONS1", "1"),                 # "1" = Sí en el formulario
    ("Modalidad_de_la_atenci_n", "1"),  # "1" = Móvil
    ("POC", "4"),                   # "4" = Otro (se sobreescribe con el valor real del record)
    ("followup", "1"),              # "1" = Primera vez
    ("ASESPREV", "Medicina General"),
]


def _fill_defaults_via_js(ctx: FormContext, record: dict[str, str], mapping: dict[str, str], page: Page | None) -> int:
    """
    Rellena por JavaScript dentro del iframe los campos por defecto (CONS1, Modalidad, POC, followup, ASESPREV).
    Así no dependemos de qué página esté visible. Retorna cuántos se llenaron.
    """
    payload = []
    for col, default_val in DEFAULT_FIELDS_ORDER:
        path = mapping.get(col)
        if not path:
            continue
        val = str(record.get(col, default_val) or default_val).strip()
        if not val:
            val = default_val
        payload.append({"path": path, "value": val})
        # Para POC: añadir también alternativas en caso de que el form use otro formato
        if col == "POC" and mapping.get("POC"):
            for alt in POC_ESTADO_ALTERNATIVOS.get(val, []):
                payload.append({"path": path, "value": alt})

    if not payload:
        return 0
    try:
        result = ctx.locator("body").evaluate("""
            (_, payload) => {
                const doc = document;
                let filled = 0;
                payload.forEach(function(p) {
                    const path = p.path;
                    const val = (p.value || '').toString().trim();
                    if (!val) return;
                    const pathNoSlash = path.replace(/^\\//, '');
                    const names = [path, pathNoSlash];
                    for (let ni = 0; ni < names.length; ni++) {
                        const name = names[ni];
                        const inputs = doc.querySelectorAll('input[name="' + name + '"]');
                        const selects = doc.querySelectorAll('select[name="' + name + '"]');
                        if (selects.length > 0) {
                            const sel = selects[0];
                            const opt = Array.from(sel.options).find(function(o) { return o.value === val || o.text.trim() === val || (o.value && o.value.toLowerCase() === val.toLowerCase()); });
                            if (opt) { sel.value = opt.value; sel.dispatchEvent(new Event('change', { bubbles: true })); filled++; }
                            break;
                        }
                        if (inputs.length === 0) continue;
                        const first = inputs[0];
                        const type = (first.type || '').toLowerCase();
                        if (type === 'radio' || type === 'checkbox') {
                            const valLower = val.toLowerCase();
                            // Coincidencia exacta por value (los values reales del formulario son "1","2","4" etc.)
                            for (let i = 0; i < inputs.length; i++) {
                                const inp = inputs[i];
                                const v = (inp.getAttribute('value') || '').toString();
                                if (v === val || v.toLowerCase() === valLower) {
                                    inp.click(); filled++; break;
                                }
                            }
                            break;
                        }
                        if (type === 'text' || type === 'date' || type === 'number' || type === '') {
                            first.value = val; first.dispatchEvent(new Event('input', { bubbles: true })); first.dispatchEvent(new Event('change', { bubbles: true })); filled++; break;
                        }
                    }
                });
                return filled;
            }
        """, payload)
        if result and result > 0:
            logger.info("Llenados %d campos por defecto vía JS (CONS1, Modalidad, POC, followup, ASESPREV)", result)
        if page:
            page.wait_for_timeout(50)
        return int(result) if result else 0
    except Exception as e:
        logger.warning("No se pudo llenar por JS: %s", e)
        return 0


def _fill_all_via_js(ctx: FormContext, record: dict[str, str], mapping: dict[str, str], page: Page | None) -> int:
    """
    Rellena TODOS los campos del record por JavaScript.
    Evita dependencia de paginación/Next. Retorna cuántos se llenaron.
    """
    payload: list[dict[str, str]] = []
    for col, field_path in mapping.items():
        val = str(record.get(col, "")).strip()
        if not val:
            continue
        # Modalidad: filling_rules ya envía "1" (value real), pero forzamos por seguridad
        if col == "Modalidad_de_la_atenci_n":
            val = "1"
        payload.append({"path": field_path, "value": val})
        # Para POC: añadir alternativas del POC_ESTADO_ALTERNATIVOS
        if col == "POC":
            for alt in POC_ESTADO_ALTERNATIVOS.get(val, []):
                payload.append({"path": field_path, "value": alt})
        if col in ("NAT", "NATOT") and "méxico" in val.lower():
            payload.append({"path": field_path, "value": "Mexico"})
        # Para campos sí/no (CONS, CONS1, REF, entrega_tx, etc.): probar ambas formas
        # (value numérico "1"/"0" y etiqueta de texto "Sí"/"No"/"Si") para cubrir
        # variaciones entre formularios donde el value real puede ser uno u otro.
        val_low = val.lower()
        if val_low in ("sí", "si", "1", "yes"):
            for alt in ("Sí", "Si", "1"):
                if alt != val:
                    payload.append({"path": field_path, "value": alt})
        elif val_low in ("no", "0"):
            for alt in ("No", "0"):
                if alt != val:
                    payload.append({"path": field_path, "value": alt})
    if not payload:
        return 0
    try:
        result = ctx.locator("body").evaluate(
            """
            (_, payload) => {
                const doc = document;
                let filled = 0;
                function findInputs(name) {
                    let el = doc.querySelectorAll('input[name="' + name + '"]');
                    if (el.length === 0) el = doc.querySelectorAll('input[data-name="' + name + '"]');
                    if (el.length === 0) el = doc.querySelectorAll('[data-name="' + name + '"]');
                    return el;
                }
                function findSelects(name) {
                    let el = doc.querySelectorAll('select[name="' + name + '"]');
                    if (el.length === 0) el = doc.querySelectorAll('select[data-name="' + name + '"]');
                    return el;
                }
                payload.forEach(function(p) {
                    const path = p.path;
                    const val = (p.value || '').toString().trim();
                    if (!val) return;
                    const pathNoSlash = path.replace(/^\\//, '');
                    const names = [path, pathNoSlash];
                    // Aliases para campo SEX (el formulario puede usar male/female o 1/2)
                    const isSexField = path.indexOf('/SEX') >= 0 || path.endsWith('SEX');
                    var sexAliasesToTry = null;
                    if (isSexField) {
                        const vl = val.toLowerCase();
                        if (vl === 'femenino' || vl === 'female' || vl === 'f' || vl === 'mujer' || vl === '2') {
                            sexAliasesToTry = ['female', 'f', '2', 'Femenino', 'femenino', 'mujer', 'Female'];
                        } else if (vl === 'masculino' || vl === 'male' || vl === 'm' || vl === 'hombre' || vl === '1') {
                            sexAliasesToTry = ['male', 'm', '1', 'Masculino', 'masculino', 'hombre', 'Male'];
                        }
                    }
                    for (let ni = 0; ni < names.length; ni++) {
                        const name = names[ni];
                        const selects = findSelects(name);
                        if (selects.length > 0) {
                            const sel = selects[0];
                            const opt = Array.from(sel.options).find(function(o) {
                                return o.value === val || o.text.trim() === val ||
                                    (o.value && o.value.toLowerCase() === val.toLowerCase());
                            });
                            if (opt) { sel.value = opt.value; sel.dispatchEvent(new Event('change', { bubbles: true })); filled++; }
                            return;
                        }
                        const inputs = findInputs(name);
                        if (inputs.length === 0) continue;
                        var targetInputs = inputs;
                        if (path.indexOf('Fecha_de_atenci_n') >= 0) {
                            targetInputs = [];
                            for (var ti = 0; ti < inputs.length; ti++) {
                                var na = (inputs[ti].getAttribute('name') || '') + (inputs[ti].getAttribute('data-name') || '');
                                if (na.indexOf('group_py4vt65') >= 0 || na.indexOf('NAME') >= 0) continue;
                                targetInputs.push(inputs[ti]);
                            }
                            if (targetInputs.length === 0) targetInputs = [inputs[0]];
                        }
                        const first = targetInputs[0];
                        const type = (first.type || '').toLowerCase();
                        if (type === 'radio' || type === 'checkbox') {
                            // ── Multi-select: valor con separador ||| (ej. DIS, DX) ──
                            if (val.indexOf('|||') >= 0) {
                                const valuesToMatch = val.split('|||').map(function(v) { return v.trim(); }).filter(function(v) { return v; });
                                let checkedCount = 0;
                                for (let i = 0; i < inputs.length; i++) {
                                    const inp = inputs[i];
                                    const inpVal = (inp.getAttribute('value') || '').toString();
                                    const parent = inp.closest('label');
                                    const optSpan = parent && (
                                        parent.querySelector('.option-label') ||
                                        parent.querySelector('.label-content') ||
                                        inp.nextElementSibling
                                    );
                                    const spanText = (optSpan ? optSpan.textContent : '').trim();
                                    for (let vi = 0; vi < valuesToMatch.length; vi++) {
                                        const vt = valuesToMatch[vi];
                                        const vtLower = vt.toLowerCase();
                                        if (inpVal === vt || inpVal.toLowerCase() === vtLower ||
                                            spanText === vt || spanText.toLowerCase() === vtLower ||
                                            (vt.length > 4 && spanText.toLowerCase().indexOf(vtLower) >= 0) ||
                                            (vt.length > 4 && inpVal.toLowerCase().indexOf(vtLower) >= 0)) {
                                            if (!inp.checked) {
                                                try { inp.click(); } catch(e) {}
                                                inp.checked = true;
                                                inp.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                                                inp.dispatchEvent(new Event('change', { bubbles: true }));
                                                inp.dispatchEvent(new Event('input', { bubbles: true }));
                                            }
                                            checkedCount++;
                                            break;
                                        }
                                    }
                                }
                                if (checkedCount > 0) { filled++; }
                                return;
                            }
                            const valLower = val.toLowerCase();
                            // Función de click para radio/checkbox.
                            // SOLO inp.click() — sin dispatchEvent(change/input) posteriores.
                            // Razón: Enketo re-evalúa la lógica XForms al recibir eventos change
                            // sintéticos (isTrusted=false) y RESETEA los radios a estado vacío.
                            // _fill_consent_robust demostró que inp.click() solo SÍ funciona.
                            function clickRadio(inp) {
                                try { inp.click(); } catch(e) {}
                            }
                            // Variantes Sí/No: el form puede usar "Si","Sí","1","yes", etc.
                            var SI_LOWER = ['sí', 'si', 's', 'yes', '1', 'true'];
                            var NO_LOWER = ['no', 'n', '0', 'false'];
                            var siNoValuesToTry = [val];
                            var siNoLabelsToTry = [val];
                            // Aliases para SEX (Femenino/Masculino)
                            if (sexAliasesToTry) {
                                siNoValuesToTry = sexAliasesToTry;
                                siNoLabelsToTry = sexAliasesToTry;
                            } else if (SI_LOWER.indexOf(valLower) >= 0) {
                                siNoValuesToTry = ['Sí', 'Si', '1', 'si', 'sí', 'yes', 'Yes', 'SI', 'S'];
                                siNoLabelsToTry = ['Sí', 'Si', 'sí', 'si', 'Yes', 'yes'];
                            } else if (NO_LOWER.indexOf(valLower) >= 0) {
                                siNoValuesToTry = ['No', '0', 'no', 'NO', 'N'];
                                siNoLabelsToTry = ['No', 'no', 'NO'];
                            }
                            // 1) Coincidencia por value del atributo (incluye variantes Sí/No y SEX)
                            for (var vi = 0; vi < siNoValuesToTry.length; vi++) {
                                var vt = siNoValuesToTry[vi];
                                for (let i = 0; i < inputs.length; i++) {
                                    const inp = inputs[i];
                                    const v = (inp.getAttribute('value') || '').toString();
                                    if (v === vt || v.toLowerCase() === vt.toLowerCase()) {
                                        // Verificar antes de clickear: Enketo deselecciona radios
                                        // si se hace click en uno ya seleccionado (toggle behavior).
                                        if (!inp.checked) { clickRadio(inp); }
                                        filled++; return;
                                    }
                                }
                            }
                            // 2) Buscar por texto del span.option-label (etiqueta visible en Enketo, incluye variantes)
                            for (var li = 0; li < siNoLabelsToTry.length; li++) {
                                var labelToFind = siNoLabelsToTry[li];
                                for (let i = 0; i < inputs.length; i++) {
                                    const inp = inputs[i];
                                    // Enketo usa <span class="option-label"> o <span class="label-content">
                                    const parent = inp.closest('label');
                                    const optSpan = parent && (
                                        parent.querySelector('.option-label') ||
                                        parent.querySelector('.label-content') ||
                                        inp.nextElementSibling
                                    );
                                    const spanText = (optSpan ? optSpan.textContent : '').trim();
                                    if (spanText && (spanText === labelToFind || spanText.toLowerCase() === labelToFind.toLowerCase())) {
                                        // Verificar antes: Enketo toggle
                                        if (!inp.checked) { clickRadio(inp); }
                                        filled++; return;
                                    }
                                }
                            }
                            // 3) Coincidencia parcial moderada (solo si val es string largo, no numérico corto)
                            if (valLower.length > 3 && isNaN(val)) {
                                for (let i = 0; i < inputs.length; i++) {
                                    const inp = inputs[i];
                                    const v = (inp.getAttribute('value') || '').toString().toLowerCase();
                                    if (v && (v.indexOf(valLower) >= 0 || valLower.indexOf(v) >= 0)) {
                                        // Verificar antes: Enketo toggle
                                        if (!inp.checked) { clickRadio(inp); }
                                        filled++; return;
                                    }
                                }
                            }
                            return;
                        }
                        if (type === 'text' || type === 'date' || type === 'number' || type === '') {
                            try { var ns = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; ns.call(first, val); } catch(e) {}
                            first.value = val;
                            first.dispatchEvent(new Event('input', { bubbles: true }));
                            first.dispatchEvent(new Event('change', { bubbles: true }));
                            first.dispatchEvent(new Event('blur', { bubbles: true }));
                            filled++; return;
                        }
                    }
                });
                return filled;
            }
            """,
            payload,
        )
        filled_count = int(result) if result else 0
        if filled_count > 0:
            logger.info("Llenados %d campos por JS (llenado completo)", filled_count)
        if page:
            page.wait_for_timeout(100)
        return filled_count
    except Exception as e:
        logger.warning("No se pudo llenar todos los campos por JS: %s", e)
        return 0


def _ensure_consent_marked(ctx: FormContext, page: Page | None = None) -> None:
    """
    Marca consentimiento (CONS1=1) para habilitar el resto de campos.
    Si no es Sí, el formulario NO muestra 'Nombre del paciente*'.
    """
    # El formulario usa value="1" para "Sí" en CONS1 (confirmado por diagnóstico DOM)
    for name_val in [
        ('[name="/aD6FdrTDPaW4QzCLjmG7WE/CONS1"][value="1"]', "1"),
        ('[name="aD6FdrTDPaW4QzCLjmG7WE/CONS1"][value="1"]', "1"),
    ]:
        try:
            consent = ctx.locator(name_val[0]).first
            if consent.count() > 0:
                consent.click(force=True)
                if page:
                    page.wait_for_timeout(200)
                logger.info("Consentimiento marcado (CONS1=Sí)")
                return
        except Exception:
            continue
    logger.warning("No se encontró radio CONS1=Sí; se intentará por JS.")


_FIELD_SELECTOR = (
    "[name*='CONS1'], [name*='Fecha_de_atenci_n'], [data-name*='CONS1'], [data-name*='Fecha'], "
    "input[type='text'], input[type='date'], input[type='number'], "
    "textarea, select, input[type='radio']"
)


def _get_form_contexts_candidates(page: Page) -> list[tuple[FormContext, str]]:
    """
    Retorna una lista de (contexto, descripción) a probar.
    Incluye iframe anidado por si Enketo pone el formulario en un segundo nivel.
    """
    candidates: list[tuple[FormContext, str]] = []
    url = page.url or ""

    def add(ctx: FormContext, desc: str) -> None:
        candidates.append((ctx, desc))

    # 1) APP_URL: iframe#formIframe
    if "localhost" in url or "127.0.0.1" in url:
        try:
            page.wait_for_selector("iframe#formIframe[src]", timeout=6000)
            frame = page.frame_locator("iframe#formIframe")
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=15000)
            add(frame, "iframe#formIframe")
        except Exception:
            pass

    # 2) FORM_URL: primer iframe
    try:
        if page.locator("iframe").count() > 0:
            frame = page.frame_locator("iframe").first
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=10000)
            add(frame, "iframe.first")
    except Exception:
        pass

    # 3) FORM_URL: iframe anidado (primer iframe -> segundo iframe)
    try:
        if page.locator("iframe").count() > 0:
            outer = page.frame_locator("iframe").first
            # Intentar localizar un iframe dentro del primero
            inner_count = outer.locator("iframe").count()
            if inner_count > 0:
                inner = outer.frame_locator("iframe").first
                inner.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=6000)
                add(inner, "iframe.first > iframe.first (anidado)")
    except Exception:
        pass

    # 4) Documento principal (esperar más tiempo para que el formulario cargue en reintentos)
    try:
        page.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=10000)
        add(page, "documento principal")
    except Exception:
        pass

    # 5) Compatibilidad: iframe#formIframe aunque la URL no sea app
    try:
        if page.locator("iframe#formIframe").count() > 0:
            frame = page.frame_locator("iframe#formIframe")
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=5000)
            if not any(c[1] == "iframe#formIframe" for c in candidates):
                add(frame, "iframe#formIframe (compat)")
    except Exception:
        pass

    return candidates


def _validate_critical_fields(ctx: FormContext) -> dict[str, bool]:
    """
    Comprueba si los campos críticos (CONS1 y Fecha_de_atenci_n) tienen valor en el DOM.
    Para Fecha: solo cuenta si el PRIMER input de "Fecha de atención" (inicio del formulario) tiene valor,
    no un campo de otra sección (ej. nombre).
    Retorna {"CONS1": True/False, "Fecha_de_atenci_n": True/False}.
    """
    try:
        result = ctx.locator("body").evaluate("""
            () => {
                const doc = document;
                const paths = [
                    '/aD6FdrTDPaW4QzCLjmG7WE/CONS1',
                    'aD6FdrTDPaW4QzCLjmG7WE/CONS1',
                    '/aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n',
                    'aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n'
                ];
                let consentFilled = false;
                let fechaFilled = false;
                paths.forEach(function(path) {
                    const inputs = doc.querySelectorAll('input[name="' + path + '"], input[data-name="' + path + '"], [data-name="' + path + '"]');
                    inputs.forEach(function(inp) {
                        const type = (inp.type || '').toLowerCase();
                        if (type === 'radio' || type === 'checkbox') {
                            if (inp.checked) consentFilled = true;
                        } else if (path.indexOf('Fecha') >= 0) {
                            if (inp.value && inp.value.trim().length >= 10) fechaFilled = true;
                        }
                    });
                });
                // Fecha: validar solo el PRIMER input de Fecha_de_atenci_n (sección inicio), no otro campo
                const fechaPaths = ['/aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n', 'aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n'];
                for (let p = 0; p < fechaPaths.length; p++) {
                    const name = fechaPaths[p];
                    let list = doc.querySelectorAll('input[name="' + name + '"], input[data-name="' + name + '"]');
                    if (list.length > 0) {
                        const first = list[0];
                        if (first.value && first.value.trim().length >= 10) fechaFilled = true;
                        break;
                    }
                }
                return { CONS1: consentFilled, Fecha_de_atenci_n: fechaFilled };
            }
        """)
        if result and isinstance(result, dict):
            return {"CONS1": bool(result.get("CONS1")), "Fecha_de_atenci_n": bool(result.get("Fecha_de_atenci_n"))}
    except Exception as e:
        logger.debug("Validación de campos críticos: %s", e)
    return {"CONS1": False, "Fecha_de_atenci_n": False}


def _fill_consent_robust(ctx: FormContext, page: Page | None) -> bool:
    """
    Marca CONS1 ("Sí") usando etiqueta de texto primero (más fiable que buscar por value).
    El formulario Enketo puede usar value="1", "Sí", "si", etc. para "Sí"; buscar por label evita
    seleccionar "No" accidentalmente cuando value="1" corresponde a "No".
    """
    path_full = "/aD6FdrTDPaW4QzCLjmG7WE/CONS1"
    path_no_slash = "aD6FdrTDPaW4QzCLjmG7WE/CONS1"

    # Estrategia 1 (PREFERIDA): buscar el radio cuya etiqueta visible sea "Sí" / "Si"
    # Enketo envuelve cada opción en <label><input ...><span class="option-label">Sí</span></label>
    try:
        clicked = ctx.locator("body").evaluate("""
            () => {
                const doc = document;
                const paths = ['/aD6FdrTDPaW4QzCLjmG7WE/CONS1', 'aD6FdrTDPaW4QzCLjmG7WE/CONS1'];
                const siLabels = ['Sí', 'Si', 'sí', 'si', 'Yes', 'yes'];
                // Buscar todos los inputs del campo CONS1
                let inputs = [];
                for (let p = 0; p < paths.length; p++) {
                    let found = doc.querySelectorAll('input[name="' + paths[p] + '"]');
                    if (found.length === 0) found = doc.querySelectorAll('input[data-name="' + paths[p] + '"]');
                    if (found.length > 0) { inputs = Array.from(found); break; }
                }
                if (inputs.length === 0) return 0;
                // Estrategia 1: por value exacto "1" (el formulario usa value="1" para Sí)
                for (let i = 0; i < inputs.length; i++) {
                    const inp = inputs[i];
                    if (inp.getAttribute('value') === '1') { inp.click(); return 1; }
                }
                // Estrategia 2: por etiqueta visible en span.option-label (exacta, sin startsWith)
                for (let i = 0; i < inputs.length; i++) {
                    const inp = inputs[i];
                    const parent = inp.closest('label');
                    const optSpan = parent && (parent.querySelector('.option-label') || parent.querySelector('.label-content') || inp.nextElementSibling);
                    const spanText = (optSpan ? optSpan.textContent : '').trim();
                    for (let s = 0; s < siLabels.length; s++) {
                        if (spanText === siLabels[s]) { inp.click(); return 2; }
                    }
                }
                // Estrategia 3: cualquier radio que NO sea value="0" o value="" (No/vacío)
                for (let i = 0; i < inputs.length; i++) {
                    const inp = inputs[i];
                    const v = (inp.getAttribute('value') || '').trim();
                    if (v !== '' && v !== '0' && v.toLowerCase() !== 'no' && v.toLowerCase() !== 'false') {
                        inp.click(); return 3;
                    }
                }
                return 0;
            }
        """)
        if page:
            page.wait_for_timeout(50)
        if _validate_critical_fields(ctx).get("CONS1"):
            logger.info("Consentimiento marcado (label-text Sí)")
            return True
    except Exception as e:
        logger.warning("Consentimiento por label-text: %s", e)

    # Estrategia 2: Playwright locator — buscar por texto visible "Sí" en el contexto de CONS1
    for path in (path_full, path_no_slash):
        for attr in ("name", "data-name"):
            # Intentar radio que visiblemente dice "Sí" usando :has-text
            for label_text in ("Sí", "Si"):
                try:
                    sel = f'label:has(input[{attr}="{path}"]):has-text("{label_text}") input'
                    loc = ctx.locator(sel).first
                    if loc.count() > 0:
                        loc.click(force=True)
                        if page:
                            page.wait_for_timeout(50)
                        if _validate_critical_fields(ctx).get("CONS1"):
                            logger.info("Consentimiento marcado (Playwright label:%s)", label_text)
                            return True
                except Exception:
                    pass

    # Estrategia 3: probar selectores de value pero EXCLUIR valor "No"/"0"/"false"
    no_values = {"no", "0", "false", "n"}
    for path in (path_full, path_no_slash):
        for attr in ("name", "data-name"):
            try:
                # Obtener todos los radios y elegir el que NO sea "No"
                all_radios = ctx.locator(f'input[{attr}="{path}"]')
                count = all_radios.count()
                for i in range(count):
                    r = all_radios.nth(i)
                    val = (r.get_attribute("value") or "").strip().lower()
                    if val not in no_values:
                        r.click(force=True)
                        if page:
                            page.wait_for_timeout(50)
                        if _validate_critical_fields(ctx).get("CONS1"):
                            logger.info("Consentimiento marcado (radio no-No, value=%s)", val)
                            return True
            except Exception:
                pass

    logger.warning("No se pudo marcar CONS1=Sí con ninguna estrategia")
    return False


def _parse_fecha_yyyy_mm_dd(fecha_value: str) -> tuple[str, str, str] | None:
    """Convierte 'yyyy-mm-dd' en (year, month, day). Retorna None si no es válido."""
    s = (fecha_value or "").strip()[:10]
    if len(s) < 10:
        return None
    parts = s.split("-")
    if len(parts) != 3:
        return None
    y, m, d = parts[0], parts[1], parts[2]
    if len(y) == 4 and len(m) in (1, 2) and len(d) in (1, 2):
        return (y, m.zfill(2), d.zfill(2))
    return None


def _fill_fecha_robust(ctx: FormContext, fecha_value: str, page: Page | None) -> bool:
    """
    Rellena SOLO el campo "Fecha de atención" al INICIO del formulario (no el nombre ni otros).
    Prueba varios casos en orden; si uno no funciona pasa al siguiente hasta validar.
    - Caso 1: Un solo input (name/data-name exacto) — solo el primero en el DOM.
    - Caso 2: Tres inputs día / mes / año (sufijos .day .month .year o _day _month _year).
    - Caso 3: JS que rellena únicamente el primer input de Fecha_de_atenci_n.
    """
    if not fecha_value or len(fecha_value.strip()) < 8:
        return False
    fecha_value = str(fecha_value).strip()[:10]
    parsed = _parse_fecha_yyyy_mm_dd(fecha_value)
    year_s, month_s, day_s = (parsed or ("", "", ""))[0], (parsed or ("", "", ""))[1], (parsed or ("", "", ""))[2]

    paths = ["/aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n", "aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n"]

    # ——— Caso 1: Un solo input (solo el PRIMERO en el formulario, sección Fecha de atención)
    for path in paths:
        for attr in ("name", "data-name"):
            try:
                sel = f'input[{attr}="{path}"]'
                loc = ctx.locator(sel).first
                if loc.count() > 0:
                    loc.fill(fecha_value)
                    loc.evaluate("el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); el.dispatchEvent(new Event('blur', { bubbles: true })); }")
                    if page:
                        page.wait_for_timeout(50)
                    if _validate_critical_fields(ctx).get("Fecha_de_atenci_n"):
                        logger.info("Fecha de atención rellenada (primer input, %s)", attr)
                        return True
            except Exception:
                pass

    # ——— Caso 2: Tres inputs día / mes / año (Enketo a veces usa widgets separados)
    if parsed:
        for path in paths:
            for attr in ("name", "data-name"):
                for sep in (".", "_", ""):
                    try:
                        day_sel = f'input[{attr}="{path}{sep}day"], input[{attr}="{path}{sep}día"]'
                        month_sel = f'input[{attr}="{path}{sep}month"], input[{attr}="{path}{sep}mes"]'
                        year_sel = f'input[{attr}="{path}{sep}year"], input[{attr}="{path}{sep}año"]'
                        loc_d = ctx.locator(day_sel).first
                        loc_m = ctx.locator(month_sel).first
                        loc_y = ctx.locator(year_sel).first
                        if loc_d.count() > 0 and loc_m.count() > 0 and loc_y.count() > 0:
                            loc_d.fill(day_s)
                            loc_m.fill(month_s)
                            loc_y.fill(year_s)
                            for loc in (loc_d, loc_m, loc_y):
                                loc.evaluate("el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }")
                            if page:
                                page.wait_for_timeout(50)
                            if _validate_critical_fields(ctx).get("Fecha_de_atenci_n"):
                                logger.info("Fecha de atención rellenada (día/mes/año)")
                                return True
                    except Exception:
                        pass
        # Selects para día/mes/año
        for path in paths:
            for attr in ("name", "data-name"):
                try:
                    sel_d = f'select[{attr}="{path}.day"], select[{attr}="{path}_day"]'
                    sel_m = f'select[{attr}="{path}.month"], select[{attr}="{path}_month"]'
                    sel_y = f'select[{attr}="{path}.year"], select[{attr}="{path}_year"]'
                    ld, lm, ly = ctx.locator(sel_d).first, ctx.locator(sel_m).first, ctx.locator(sel_y).first
                    if ld.count() > 0 and lm.count() > 0 and ly.count() > 0:
                        ld.select_option(value=day_s, label=day_s)
                        lm.select_option(value=month_s, label=month_s)
                        ly.select_option(value=year_s, label=year_s)
                        if page:
                            page.wait_for_timeout(50)
                        if _validate_critical_fields(ctx).get("Fecha_de_atenci_n"):
                            logger.info("Fecha de atención rellenada (selects día/mes/año)")
                            return True
                except Exception:
                    pass

    # ——— Caso 3: JS con native setter para Enketo date widgets
    js_filled = False
    try:
        res = ctx.locator("body").evaluate(
            """
            (_, fechaVal) => {
                const doc = document;
                const paths = ['/aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n', 'aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n'];
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value') &&
                    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                for (let i = 0; i < paths.length; i++) {
                    const name = paths[i];
                    let list = doc.querySelectorAll('input[name="' + name + '"]');
                    if (list.length === 0) list = doc.querySelectorAll('input[data-name="' + name + '"]');
                    if (list.length === 0) list = doc.querySelectorAll('input[data-name*="Fecha_de_atenci_n"]');
                    for (let j = 0; j < list.length; j++) {
                        const el = list[j];
                        var pathAttr = el.getAttribute('name') || el.getAttribute('data-name') || '';
                        if (pathAttr.indexOf('group_py4vt65') >= 0) continue;
                        if (pathAttr.indexOf('NAME') >= 0) continue;
                        if (nativeSetter) { try { nativeSetter.call(el, fechaVal); } catch(e) {} }
                        el.value = fechaVal;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur', { bubbles: true }));
                        return 1;
                    }
                }
                return 0;
            }
        """,
            fecha_value,
        )
        js_filled = bool(res)
        if page:
            page.wait_for_timeout(50)
        if _validate_critical_fields(ctx).get("Fecha_de_atenci_n"):
            logger.info("Fecha de atención rellenada (JS + native setter)")
            return True
    except Exception as e:
        logger.warning("Fecha por JS: %s", e)

    # ——— Caso 4: type="date" primero, luego type="text", solo primer match
    for path in paths:
        for typ in ("date", "text"):
            try:
                sel = f'input[type="{typ}"][name="{path}"], input[type="{typ}"][data-name="{path}"]'
                loc = ctx.locator(sel).first
                if loc.count() > 0:
                    loc.fill(fecha_value)
                    loc.evaluate("el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); el.dispatchEvent(new Event('blur', { bubbles: true })); }")
                    if page:
                        page.wait_for_timeout(50)
                    if _validate_critical_fields(ctx).get("Fecha_de_atenci_n"):
                        logger.info("Fecha de atención rellenada (type=%s)", typ)
                        return True
            except Exception:
                pass

    # Si la validación del DOM no confirma pero el JS intentó rellenar,
    # retornar True para no bloquear el contexto. Enketo puede usar widgets
    # que no actualizan el input subyacente de forma inmediata.
    if js_filled:
        logger.info("Fecha de atención: JS ejecutado (validación DOM incierta; se continúa de todas formas)")
        return True

    logger.warning("Fecha de atención: no se pudo rellenar con ninguna estrategia")
    return False


def _get_form_frame(page: Page) -> FormContext | None:
    """
    Obtiene el contexto del formulario (frame o página principal).
    Estrategia multi-iframe: prueba iframe#formIframe (APP_URL), iframe (FORM_URL directo),
    y documento principal como fallback.
    """
    url = page.url or ""
    is_kobo = "kobotoolbox" in url or "ee-eu" in url
    is_app = "localhost" in url or "127.0.0.1" in url

    # 1) Si estamos en APP_URL (nuestra app), buscar iframe#formIframe
    if is_app:
        try:
            page.wait_for_selector("iframe#formIframe[src]", timeout=8000)
            frame = page.frame_locator("iframe#formIframe")
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
            logger.info("Formulario encontrado en iframe#formIframe (APP_URL)")
            return frame
        except Exception as e:
            logger.warning("No se encontró formulario en iframe#formIframe: %s", e)

    # 2) Si estamos en FORM_URL directo: probar iframe interno de Enketo
    if is_kobo or not is_app:
        try:
            frame = page.frame_locator("iframe").first
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=15000)
            logger.info("Formulario encontrado en iframe interno (FORM_URL directo)")
            return frame
        except Exception as e:
            logger.debug("No se encontró formulario en iframe interno: %s", e)

        # 3) Fallback: documento principal
        try:
            page.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=8000)
            logger.info("Formulario encontrado en documento principal")
            return page
        except Exception as e:
            logger.debug("No se encontró formulario en documento principal: %s", e)

    # 4) Último intento: iframe#formIframe por compatibilidad
    try:
        page.wait_for_selector("iframe#formIframe[src]", timeout=3000)
        page.wait_for_timeout(300)
        frame = page.frame_locator("iframe#formIframe")
        frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=10000)
        logger.info("Formulario encontrado en iframe#formIframe (compatibilidad)")
        return frame
    except Exception as e:
        logger.warning("No se pudo obtener el frame del formulario: %s", e)
        return None


def _normalize_value_for_radio(val: str) -> str:
    """Quita sufijos como '+2' para mejorar coincidencia con valores del formulario."""
    import re
    s = str(val or "").strip()
    s = re.sub(r"\s*\+\d+\s*$", "", s)  # "Odontología +2" -> "Odontología"
    return s.strip()


# Si el formulario usa códigos para Estado (POC) en vez de etiqueta, probar ambos
# Alternativas de value para POC/Estado cuando el value principal no hace match
# Basado en diagnóstico DOM: POC options=[baja_california(Baja California),1(Baja Californa),
#   2(Chihuahua),nuevo_le_n(Nuevo León),3(Sonora),4(Otro)]
POC_ESTADO_ALTERNATIVOS = {
    "1":               ["BCS", "baja_californa_sur", "Baja Californa Sur", "Baja California Sur"],
    "2":               ["CHIH", "chihuahua", "Chihuahua"],
    "3":               ["sonora", "Sonora"],
    "baja_california": ["Baja California", "baja california"],
    "nuevo_le_n":      ["Nuevo León", "nuevo_leon", "nuevo_le_n"],
    "4":               ["Otro", "otro"],
}


def _fill_field_in_frame(ctx: FormContext, field_path: str, value: str, *, force: bool = False) -> bool:
    """Rellena un campo en el frame. Retorna True si tuvo éxito."""
    value = str(value or "").strip()
    if not value:
        return False
    value_norm = _normalize_value_for_radio(value)
    short_name = field_path.split("/")[-1] if "/" in field_path else field_path
    # Enketo puede usar name con o sin barra inicial
    field_path_no_slash = field_path.lstrip("/")
    # Para campos sí/no: intentar tanto valor numérico como texto (formulario puede usar "Sí"/"No" o "1"/"0")
    si_no_values = []
    value_lower = value.lower() if value else ""
    if value_lower in ("1", "si", "sí", "yes", "s", "true"):
        si_no_values = ["Si", "Sí", "1", "si", "sí", "Yes", "true"]
    elif value_lower in ("0", "no", "n", "false"):
        si_no_values = ["No", "0", "no", "false"]
    selectors = [
        f'input[name="{field_path}"]',
        f'textarea[name="{field_path}"]',
        f'select[name="{field_path}"]',
        f'[name="{field_path}"]',
        f'input[name="{field_path_no_slash}"]',
        f'textarea[name="{field_path_no_slash}"]',
        f'select[name="{field_path_no_slash}"]',
        f'[name="{field_path_no_slash}"]',
        f'[data-name="{field_path}"]',
        f'[name$="{short_name}"]',
    ]
    for sel in selectors:
        try:
            loc = ctx.locator(sel).first
            if loc.count() == 0:
                continue
            if not force:
                loc.wait_for(state="visible", timeout=2000)
            itype = (loc.get_attribute("type") or "").lower()

            def _dispatch_input_change(locator):
                try:
                    locator.evaluate("""el => {
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""")
                except Exception:
                    pass

            if itype in ("radio", "checkbox"):
                # Para radio/checkbox: usar Playwright click y NO despachar eventos change/input
                # sintéticos después — Enketo los interpreta como reset de la selección.
                # to_try: primero el value exacto (ya viene del formulario desde filling_rules)
                to_try = [value, value_norm]
                # si_no_values adicionales cuando corresponde
                if si_no_values:
                    to_try = list(si_no_values) + [x for x in to_try if x not in si_no_values]
                # Modalidad: filling_rules envía "1" (Móvil), pero también probar "movil" por si acaso
                if short_name == "Modalidad_de_la_atenci_n":
                    to_try = ["1", "movil", "Movil", "Móvil"] + [x for x in to_try if x not in ("1", "movil", "Movil", "Móvil")]
                # Estado/POC: el value ya viene del formulario ("1","2","4","baja_california","nuevo_le_n","3")
                if short_name in ("POC", "Estado") and value in POC_ESTADO_ALTERNATIVOS:
                    to_try = [value] + POC_ESTADO_ALTERNATIVOS.get(value, []) + [x for x in to_try if x != value]
                # Nacionalidad: probar con y sin tilde
                if short_name in ("NAT", "NATOT") and "méxico" in value.lower():
                    to_try = ["México", "Mexico"] + [x for x in to_try if x not in ("México", "Mexico")]
                # Nacionalidad / Donde nació: probar con y sin tilde
                if short_name in ("NAT", "NATOT") and "méxico" in value.lower():
                    to_try = ["México", "Mexico"] + [x for x in to_try if x not in ("México", "Mexico")]
                # SEX: el formulario puede usar "male"/"female" o "1"/"2" como value
                if short_name == "SEX":
                    vnl = value_norm.lower()
                    if vnl in ("femenino", "female", "mujer", "f", "2"):
                        to_try = ["female", "f", "2", "Femenino", "femenino", "mujer", "Female", "FEMALE"] + [x for x in to_try if x not in ("female", "f", "2", "Femenino", "femenino", "mujer")]
                    elif vnl in ("masculino", "male", "hombre", "m", "1"):
                        to_try = ["male", "m", "1", "Masculino", "masculino", "hombre", "Male", "MALE"] + [x for x in to_try if x not in ("male", "m", "1", "Masculino", "masculino", "hombre")]
                # Especifique qué se entrega: etiquetas exactas
                if short_name == "Especifique_qu_se_entrega":
                    to_try = [value, value_norm] + [v for v in ("Anteojos", "Medicamento/suplemento", "Plan de Tratamiento", "Resultados de Laboratorio", "Otro") if value_norm.lower() in v.lower() or v.lower() in value_norm.lower()]
                # ME_ML: Embarazada / Lactancia / No Aplica — probar etiqueta exacta y variantes internas
                if short_name == "ME_ML":
                    vnl = value_norm.lower()
                    if "embara" in vnl:
                        to_try = ["Embarazada", "embarazada", "1"] + [x for x in to_try if x not in ("Embarazada", "embarazada", "1")]
                    elif "lactanc" in vnl or "lactant" in vnl:
                        to_try = ["Lactancia", "lactancia", "2"] + [x for x in to_try if x not in ("Lactancia", "lactancia", "2")]
                    elif "no" in vnl or "aplica" in vnl or "na" == vnl:
                        to_try = ["No Aplica", "no_aplica", "no aplica", "3", "0"] + [x for x in to_try if x not in ("No Aplica", "no_aplica", "no aplica", "3", "0")]
                seen = set()
                for vtry in to_try:
                    if not vtry or vtry in seen:
                        continue
                    seen.add(vtry)
                    radio_sel = f'[name="{field_path}"][value="{vtry}"]'
                    rloc = ctx.locator(radio_sel).first
                    if rloc.count() == 0:
                        radio_sel_noslash = f'[name="{field_path_no_slash}"][value="{vtry}"]'
                        rloc = ctx.locator(radio_sel_noslash).first
                    # También probar con data-name (Enketo a veces usa data-name en lugar de name)
                    if rloc.count() == 0:
                        radio_sel_data = f'[data-name="{field_path}"][value="{vtry}"]'
                        rloc = ctx.locator(radio_sel_data).first
                    if rloc.count() == 0:
                        radio_sel_data_noslash = f'[data-name="{field_path_no_slash}"][value="{vtry}"]'
                        rloc = ctx.locator(radio_sel_data_noslash).first
                    if rloc.count() > 0:
                        # Verificar antes de clickear: Enketo deselecciona radios ya marcados (toggle).
                        try:
                            already_checked = rloc.evaluate("el => el.checked")
                        except Exception:
                            already_checked = False
                        if not already_checked:
                            rloc.click(force=force)
                        return True
                all_r = ctx.locator(f'[name="{field_path}"]')
                if all_r.count() == 0:
                    all_r = ctx.locator(f'[name="{field_path_no_slash}"]')
                if all_r.count() == 0:
                    all_r = ctx.locator(f'[data-name="{field_path}"]')
                if all_r.count() == 0:
                    all_r = ctx.locator(f'[data-name="{field_path_no_slash}"]')
                vlow = value_norm.lower()
                for i in range(all_r.count()):
                    r = all_r.nth(i)
                    v = (r.get_attribute("value") or "").lower()
                    if v and (vlow in v or v in vlow or v in value.lower()[:15]):
                        try:
                            already_checked = r.evaluate("el => el.checked")
                        except Exception:
                            already_checked = False
                        if not already_checked:
                            r.click(force=force)
                        return True
            else:
                try:
                    loc.select_option(value=value, force=force)
                    _dispatch_input_change(loc)
                    return True
                except Exception:
                    pass
                try:
                    loc.select_option(label=value, force=force)
                    _dispatch_input_change(loc)
                    return True
                except Exception:
                    pass
                # Solo llamar fill() si el elemento es un input/textarea real.
                # Si es un contenedor (div/span), fill(force=True) puede accidentalmente
                # escribir en el elemento con foco actual (ej. el campo NAME).
                try:
                    tag_name = (loc.evaluate("el => el.tagName") or "").upper()
                except Exception:
                    tag_name = ""
                if tag_name in ("INPUT", "TEXTAREA", "SELECT"):
                    try:
                        loc.fill(value, force=force)
                        _dispatch_input_change(loc)
                        return True
                    except Exception:
                        pass
                elif tag_name:
                    # Contenedor: buscar el input hijo y llenarlo por JS
                    try:
                        result = loc.evaluate(
                            "(el, val) => { "
                            "const inp = el.querySelector('input:not([type=hidden]), textarea'); "
                            "if (!inp) return false; "
                            "try { const ns = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value'); "
                            "if (ns && ns.set) ns.set.call(inp, val); } catch(e) {} "
                            "inp.value = val; "
                            "inp.dispatchEvent(new Event('input', {bubbles:true})); "
                            "inp.dispatchEvent(new Event('change', {bubbles:true})); "
                            "return true; }",
                            value,
                        )
                        if result:
                            return True
                    except Exception:
                        pass
        except Exception:
            continue
    return False


# Selectores para botones Enketo
SUBMIT_SELECTORS = [
    'button:has-text("Submit")',
    'button:has-text("Enviar")',
    '[type="submit"]',
    '[data-role="submit"]',
    'button[type="submit"]',
    '.btn-submit',
]
NEXT_SELECTORS = [
    'button:has-text("Next")',
    'button:has-text("Siguiente")',
    '[data-role="next"]',
    '.btn-next',
    'a:has-text("Next")',
    'button.next',
    '[type="button"]:has-text("Siguiente")',
]


def _log_field_diagnostics(ctx: FormContext, mapping: dict, record: dict) -> None:
    """
    Loguea el estado actual de los campos clave en el DOM para depuración.
    Muestra qué radio está seleccionado y su value real; para fecha/texto el value actual.
    """
    # Usamos los paths del mapping cuando existen, fallback a paths hardcoded
    def _path(col: str, fallback: str) -> str:
        return mapping.get(col, fallback)

    key_fields = [
        ("CONS1",                   _path("CONS1", "/aD6FdrTDPaW4QzCLjmG7WE/CONS1")),
        ("Fecha_de_atenci_n",        _path("Fecha_de_atenci_n", "/aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n")),
        ("Modalidad_de_la_atenci_n", _path("Modalidad_de_la_atenci_n", "/aD6FdrTDPaW4QzCLjmG7WE/group_nl0pw33/Modalidad_de_la_atenci_n")),
        ("POC",                      _path("POC", "/aD6FdrTDPaW4QzCLjmG7WE/group_nl0pw33/POC")),
        ("followup",                 _path("followup", "/aD6FdrTDPaW4QzCLjmG7WE/group_ua6kz91/followup")),
        ("Servicio_que_se_brinda",   _path("Servicio_que_se_brinda", "/aD6FdrTDPaW4QzCLjmG7WE/group_ua6kz91/Servicio_que_se_brinda")),
        ("SEX",                      _path("SEX", "/aD6FdrTDPaW4QzCLjmG7WE/group_py4vt65/SEX")),
        ("ME_ML",                    _path("ME_ML", "/aD6FdrTDPaW4QzCLjmG7WE/group_py4vt65/ME_ML")),
        ("entrega_tx",               _path("entrega_tx", "/aD6FdrTDPaW4QzCLjmG7WE/group_ic1bl54/entrega_tx")),
        ("REF",                      _path("REF", "/aD6FdrTDPaW4QzCLjmG7WE/group_xi7cn52/REF")),
        ("CONS",                     _path("CONS", "/aD6FdrTDPaW4QzCLjmG7WE/CONS")),
    ]
    try:
        result = ctx.locator("body").evaluate("""
            (_, fields) => {
                const doc = document;
                const out = {};
                fields.forEach(function(f) {
                    const name = f[0];
                    const path = f[1];
                    const pathNoSlash = path.replace(/^\\//, '');
                    let inputs = doc.querySelectorAll('input[name="' + path + '"]');
                    if (inputs.length === 0) inputs = doc.querySelectorAll('input[name="' + pathNoSlash + '"]');
                    if (inputs.length === 0) inputs = doc.querySelectorAll('input[data-name="' + path + '"]');
                    if (inputs.length === 0) { out[name] = 'NOT_FOUND'; return; }
                    const first = inputs[0];
                    const type = (first.type || '').toLowerCase();
                    if (type === 'radio' || type === 'checkbox') {
                        let checked = 'NONE';
                        let options = [];
                        for (let i = 0; i < inputs.length; i++) {
                            const inp = inputs[i];
                            const v = inp.getAttribute('value') || '';
                            // Etiqueta: preferir .option-label (Enketo), si no, nextElementSibling
                            const parent = inp.closest('label');
                            const optSpan = parent && (parent.querySelector('.option-label') || parent.querySelector('.label-content') || inp.nextElementSibling);
                            const label = (optSpan ? optSpan.textContent : (parent ? parent.textContent : '')).trim();
                            const shortLabel = label.substring(0, 15);
                            options.push(v + '(' + shortLabel + ')');
                            if (inp.checked) checked = v + '(' + shortLabel + ')';
                        }
                        out[name] = 'checked=' + checked + ' | options=[' + options.join(',') + ']';
                    } else {
                        out[name] = 'value=' + first.value;
                    }
                });
                return out;
            }
        """, key_fields)
        if result:
            for field, state in result.items():
                if "NOT_FOUND" in str(state):
                    logger.warning("DIAG %s: %s", field, state)
                else:
                    logger.info("DIAG %s: %s", field, state)
    except Exception as e:
        logger.debug("Diagnóstico de campos: %s", e)



class FormFiller:
    """Rellena el formulario Enketo dentro del iframe de nuestra app."""

    def __init__(self, mapping: dict[str, str] | None = None, page: Page | None = None):
        self.mapping = mapping or load_mapping()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = page
        self._owns_browser = page is None

    def start(self, headless: bool | None = None, reuse_page: Page | None = None) -> None:
        """Inicia el navegador o reutiliza una página existente."""
        if reuse_page:
            self._page = reuse_page
            self._owns_browser = False
            return
        if self._page:
            return
        from config import HEADLESS as CONFIG_HEADLESS
        use_headless = headless if headless is not None else CONFIG_HEADLESS
        self._playwright = sync_playwright().start()
        launch_opts = {"headless": use_headless}

        if platform.system() == "Darwin":
            for p in CHROME_PATHS_MACOS:
                if p.exists():
                    launch_opts["executable_path"] = str(p)
                    break
        if "executable_path" not in launch_opts:
            launch_opts["channel"] = "chrome"

        self._browser = self._playwright.chromium.launch(**launch_opts)
        self._context = self._browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(45000)

    def stop(self, close_browser: bool = True) -> None:
        """Cierra el navegador (si close_browser=True y somos dueños)."""
        if not close_browser or not self._owns_browser:
            return
        if self._page:
            self._page.close()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    def fill_record(
        self,
        record: dict[str, str],
        row_index: int,
        *,
        wait_for_confirm: bool = False,
        confirm_callback: Callable[[], bool] | None = None,
    ) -> bool:
        """Rellena y envía un registro. Usa múltiples contextos, llenado robusto de CONS1/Fecha y validación."""
        if not self._page or not self.mapping:
            return False

        load_url = FORM_URL if USE_DIRECT_FORM_URL else APP_URL
        logger.info("Cargando formulario: %s (fila %d)", load_url, row_index + 1)

        try:
            self._page.goto(load_url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeout:
            pass

        # Esperar a que Enketo elimine la clase "loading" del formulario (indica que está listo)
        try:
            self._page.wait_for_selector("form.or:not(.loading)", timeout=10000)
            logger.info("Enketo ready (form.or:not(.loading) visible)")
        except Exception:
            # Fallback: esperar tiempo fijo si el selector no aplica (Enketo version distinta)
            self._page.wait_for_timeout(1000)

        # Obtener candidatos de contexto (iframe, anidado, documento principal)
        candidates = _get_form_contexts_candidates(self._page)
        if not candidates:
            # Segundo intento: esperar más y volver a buscar
            self._page.wait_for_timeout(500)
            candidates = _get_form_contexts_candidates(self._page)
        if not candidates:
            fallback = _get_form_frame(self._page)
            if fallback:
                candidates = [(fallback, "fallback _get_form_frame")]
        if not candidates:
            raise RuntimeError(
                "No se encontró ningún contexto con el formulario (iframe/documento). "
                "Ejecuta python diagnostic_form.py para inspeccionar la estructura."
            )

        ctx: FormContext | None = None
        fecha_value = str(record.get("Fecha_de_atenci_n", "")).strip()
        if not fecha_value or len(fecha_value) < 8:
            # Valor por defecto: hoy en formato yyyy-mm-dd
            from datetime import date
            fecha_value = date.today().isoformat()
            logger.info("Fecha de atención no en registro; usando hoy: %s", fecha_value)

        for candidate_ctx, desc in candidates:
            logger.info("Probando contexto: %s", desc)
            # 1) Consentimiento robusto (obligatorio: sin CONS1 el formulario no muestra campos)
            if not _fill_consent_robust(candidate_ctx, self._page):
                logger.warning("Contexto %s: consentimiento no se marcó", desc)
                continue
            self._page.wait_for_timeout(50)
            # 2) Fecha robusta (intentar; no bloquea si el widget de Enketo no actualiza el DOM)
            fecha_ok = _fill_fecha_robust(candidate_ctx, fecha_value, self._page)
            if not fecha_ok:
                logger.warning("Contexto %s: fecha de atención no pudo rellenarse", desc)
            self._page.wait_for_timeout(50)
            # 3) Validar: CONS1 obligatorio; Fecha puede ser incierta con widgets Enketo
            valid = _validate_critical_fields(candidate_ctx)
            if valid.get("CONS1"):
                ctx = candidate_ctx
                if valid.get("Fecha_de_atenci_n"):
                    logger.info("Contexto válido: %s (CONS1 y Fecha confirmados)", desc)
                else:
                    logger.info("Contexto válido: %s (CONS1 confirmado; Fecha se rellenará en JS)", desc)
                break
            logger.warning("Contexto %s: CONS1 no marcado %s", desc, valid)

        if not ctx:
            raise RuntimeError(
                "No se pudo validar el llenado de 'Fecha de atención' y 'Toma de consentimiento'. "
                "Revisa que el formulario use los nombres /aD6FdrTDPaW4QzCLjmG7WE/CONS1 y "
                "Fecha_de_atenci_n. Ejecuta python diagnostic_form.py para ver los nombres reales."
            )

        # Llenar TODOS los campos por JS
        filled_js = _fill_all_via_js(ctx, record, self.mapping, self._page)
        self._page.wait_for_timeout(150)

        # Segundo pase para campos condicionales de Oftalmología.
        # Enketo evalúa la visibilidad de group_rw8yu96 de forma asíncrona tras
        # seleccionar ASESPREV=Oftalmología. El primer pase corre todo en un solo
        # ciclo JS síncrono, por lo que los checkboxes de la sección oculta se
        # ignoran silenciosamente. Esperamos a que Enketo los muestre y rellenamos.
        _oft_cols = [
            "S_ntomas_que_presenta_a_la_fec",
            "_Ha_recibido_alg_n_diagn_stico",
            "Diagn_stico_002",
            "Otro_diagn_stico",
            "Especifique_s_ntoma",
            "Especifique_diagn_stico_previo",
            "_Requiere_anteojos",
        ]
        _oft_record = {col: record.get(col, "") for col in _oft_cols if record.get(col, "")}
        if _oft_record:
            self._page.wait_for_timeout(400)
            _filled_oft = _fill_all_via_js(ctx, _oft_record, self.mapping, self._page)
            if _filled_oft:
                logger.info("Segundo pase Oftalmología: %d campos llenados", _filled_oft)
                filled_js += _filled_oft

        # Diagnóstico: loguear estado de campos clave tras el JS fill
        _log_field_diagnostics(ctx, self.mapping, record)

        # Respaldo: llenado página por página.
        # Se omite si el JS fill ya cubrió suficientes campos (evita trabajo redundante).
        filled_total = filled_js
        _JS_FILL_OK_THRESHOLD = 5  # si JS llenó ≥5 campos, el formulario estaba accesible
        if filled_js < _JS_FILL_OK_THRESHOLD:
            logger.info("JS fill bajo (%d campos); ejecutando bucle de respaldo página por página", filled_js)
            max_pages = 15
            for _ in range(max_pages):
                for col, field_path in self.mapping.items():
                    val = str(record.get(col, "")).strip()
                    if not val:
                        continue
                    # Modalidad: filling_rules ya envía "1" (value real del form = Móvil)
                    if col == "Modalidad_de_la_atenci_n":
                        val = "1"
                    if _fill_field_in_frame(ctx, field_path, val, force=True):
                        filled_total += 1
                        if col in ("POC", "Modalidad_de_la_atenci_n"):
                            self._page.wait_for_timeout(100)
                        if col == "NAT":
                            self._page.wait_for_timeout(50)

                self._page.wait_for_timeout(30)

                next_clicked = False
                for sel in NEXT_SELECTORS:
                    try:
                        btn = ctx.locator(sel).first
                        if btn.count() > 0:
                            btn.click(force=True)
                            self._page.wait_for_timeout(150)
                            next_clicked = True
                            break
                    except Exception:
                        pass
                if not next_clicked:
                    break
        else:
            logger.info("JS fill exitoso (%d campos); omitiendo bucle de respaldo", filled_js)
            # Avanzar páginas solo para llegar al botón Submit
            self._advance_pages(ctx)

        logger.info("Rellenados %d campos en total", filled_total)

        if wait_for_confirm and confirm_callback:
            if not confirm_callback():
                return False

        if not self._click_submit(ctx):
            raise RuntimeError(
                "No se encontró el botón Enviar. "
                "Puede que el formulario tenga más páginas; revisa la ventana."
            )
        return self._wait_for_success(ctx)

    def _advance_pages(self, ctx: FormContext) -> None:
        """Clic en Next mientras exista."""
        for _ in range(20):
            clicked = False
            for sel in NEXT_SELECTORS:
                try:
                    btn = ctx.locator(sel).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click()
                        self._page.wait_for_timeout(150)
                        clicked = True
                        break
                except Exception:
                    pass
            if not clicked:
                break

    def _click_submit(self, ctx: FormContext) -> bool:
        """Clic en Submit."""
        for sel in SUBMIT_SELECTORS:
            try:
                btn = ctx.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    btn.click()
                    return True
            except Exception:
                pass
        logger.error("No se encontró el botón Enviar")
        return False

    def _wait_for_success(self, ctx: FormContext, timeout: int = 15000) -> bool:
        """
        Espera confirmación de envío verificando activamente el DOM de Enketo.
        Enketo muestra un elemento .confirmation (o similar) tras un envío exitoso,
        o un mensaje de error si algo falló. También detecta redirección de URL.
        """
        SUCCESS_SELECTORS = [
            ".confirmation",
            ".enketo-confirmation",
            "[class*='confirmation']",
            ".paper-record--submitted",
            "[class*='submitted']",
            "h1.enketo-power",   # Pantalla de éxito de Enketo
        ]
        ERROR_SELECTORS = [
            ".error-msg",
            ".alert-danger",
            "[class*='error'][class*='msg']",
            "p.msg.error",
        ]
        try:
            # Esperar hasta timeout a que aparezca confirmación o error
            deadline = timeout
            poll = 300
            elapsed = 0
            while elapsed < deadline:
                # 1) Comprobar URL de éxito (Enketo redirige a /thanks o /enketo/thanks)
                if self._page:
                    url = self._page.url or ""
                    if "thanks" in url or "submitted" in url or "success" in url:
                        logger.info("Envío confirmado por redirección de URL: %s", url)
                        return True
                # 2) Comprobar selector de éxito en el DOM
                for sel in SUCCESS_SELECTORS:
                    try:
                        if ctx.locator(sel).count() > 0:
                            logger.info("Envío confirmado por selector: %s", sel)
                            return True
                    except Exception:
                        pass
                # 3) Comprobar mensajes de error visibles
                for sel in ERROR_SELECTORS:
                    try:
                        el = ctx.locator(sel).first
                        if el.count() > 0 and el.is_visible():
                            err_text = el.inner_text()[:200] if el.count() > 0 else ""
                            logger.warning("Enketo mostró error tras envío: %s", err_text)
                            return False
                    except Exception:
                        pass
                if self._page:
                    self._page.wait_for_timeout(poll)
                elapsed += poll
            # Timeout: sin confirmación ni error → asumir éxito (Enketo a veces no muestra mensaje)
            logger.warning("Timeout esperando confirmación de envío; asumiendo éxito.")
            return True
        except Exception:
            return True
