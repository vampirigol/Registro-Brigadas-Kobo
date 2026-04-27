"""
Funciones auxiliares para el llenado del formulario Enketo.
Incluye: JS fill (todos los campos, defaults), consentimiento robusto,
llenado de fecha, navegación de frames y llenado campo por campo.
"""

import logging
import re
from typing import Union

from playwright.sync_api import FrameLocator, Page, TimeoutError as PlaywrightTimeout

from config import APP_URL, FORM_URL
from ._constants import (
    FormContext,
    DEFAULT_FIELDS_ORDER,
    _FIELD_SELECTOR,
    POC_ESTADO_ALTERNATIVOS,
    SUBMIT_SELECTORS,
    NEXT_SELECTORS,
)

logger = logging.getLogger(__name__)


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
                    page.wait_for_timeout(50)
                logger.info("Consentimiento marcado (CONS1=Sí)")
                return
        except Exception:
            continue
    logger.warning("No se encontró radio CONS1=Sí; se intentará por JS.")



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
            page.wait_for_selector("iframe#formIframe[src]", timeout=20000)
            page.wait_for_timeout(700)
            frame = page.frame_locator("iframe#formIframe")
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
            add(frame, "iframe#formIframe")
        except Exception:
            pass

    # 2) FORM_URL: primer iframe
    try:
        if page.locator("iframe").count() > 0:
            frame = page.frame_locator("iframe").first
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
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
                inner.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
                add(inner, "iframe.first > iframe.first (anidado)")
    except Exception:
        pass

    # 4) Documento principal (esperar más tiempo para que el formulario cargue en reintentos)
    try:
        page.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
        add(page, "documento principal")
    except Exception:
        pass

    # 5) Compatibilidad: iframe#formIframe aunque la URL no sea app
    try:
        if page.locator("iframe#formIframe").count() > 0:
            frame = page.frame_locator("iframe#formIframe")
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
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

    # ——— Caso 1 (PRIORITARIO): JS con native setter — evita la espera del date-picker widget.
    # Enketo usa un date-picker que bloquea la interacción directa; el native setter JS
    # bypasea el widget y escribe directo en el input subyacente sin timeout de UI.
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

    # ——— Caso 2: Un solo input con force=True (no bloquea si el widget rechaza interacción)
    for path in paths:
        for attr in ("name", "data-name"):
            try:
                sel = f'input[{attr}="{path}"]'
                loc = ctx.locator(sel).first
                if loc.count() > 0:
                    loc.fill(fecha_value, force=True)
                    loc.evaluate("el => { el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); el.dispatchEvent(new Event('blur', { bubbles: true })); }")
                    if page:
                        page.wait_for_timeout(50)
                    if _validate_critical_fields(ctx).get("Fecha_de_atenci_n"):
                        logger.info("Fecha de atención rellenada (primer input force, %s)", attr)
                        return True
            except Exception:
                pass

    # ——— Caso 3: Tres inputs día / mes / año (Enketo a veces usa widgets separados)
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
                            loc_d.fill(day_s, force=True)
                            loc_m.fill(month_s, force=True)
                            loc_y.fill(year_s, force=True)
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

    # ——— Caso 4: type="date" / type="text" con force=True como último recurso
    for path in paths:
        for typ in ("date", "text"):
            try:
                sel = f'input[type="{typ}"][name="{path}"], input[type="{typ}"][data-name="{path}"]'
                loc = ctx.locator(sel).first
                if loc.count() > 0:
                    loc.fill(fecha_value, force=True)
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
            page.wait_for_selector("iframe#formIframe[src]", timeout=20000)
            page.wait_for_timeout(700)
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
            frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
            logger.info("Formulario encontrado en iframe interno (FORM_URL directo)")
            return frame
        except Exception as e:
            logger.debug("No se encontró formulario en iframe interno: %s", e)

        # 3) Fallback: documento principal
        try:
            page.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=20000)
            logger.info("Formulario encontrado en documento principal")
            return page
        except Exception as e:
            logger.debug("No se encontró formulario en documento principal: %s", e)

    # 4) Último intento: iframe#formIframe por compatibilidad
    try:
        page.wait_for_selector("iframe#formIframe[src]", timeout=12000)
        page.wait_for_timeout(500)
        frame = page.frame_locator("iframe#formIframe")
        frame.locator(_FIELD_SELECTOR).first.wait_for(state="visible", timeout=15000)
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
                    # Usar JS evaluate primero: evita simulación de teclado que puede
                    # escribir en el campo NAME cuando el input de DOB (binding oculto
                    # del date picker de Enketo) no puede recibir foco.
                    try:
                        _js_ok = loc.evaluate(
                            "(el, val) => { "
                            "try { const ns = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value'); "
                            "if (ns && ns.set) ns.set.call(el, val); } catch(e) {} "
                            "el.value = val; "
                            "el.dispatchEvent(new Event('input', {bubbles:true})); "
                            "el.dispatchEvent(new Event('change', {bubbles:true})); "
                            "return true; }",
                            value,
                        )
                        if _js_ok:
                            return True
                    except Exception:
                        pass
                    # Fallback: fill() solo si JS falló
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


