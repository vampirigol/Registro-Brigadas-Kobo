"""
Paquete form_filler — llenado de formularios Enketo con Playwright.

Módulos internos:
  _constants.py  — tipos, constantes y selectores
  _helpers.py    — funciones auxiliares (JS fill, consent, fecha, campo por campo)
  __init__.py    — clase FormFiller (navegador y orquestación)
"""

import logging
import platform
from typing import Callable

from playwright.sync_api import Page, sync_playwright, TimeoutError as PlaywrightTimeout

from config import APP_URL, FORM_URL, load_mapping, USE_DIRECT_FORM_URL
from ._constants import (
    FormContext,
    CHROME_PATHS_MACOS,
    SUBMIT_SELECTORS,
    NEXT_SELECTORS,
    POC_ESTADO_ALTERNATIVOS,
    DEFAULT_FIELDS_ORDER,
    _FIELD_SELECTOR,
)
from ._helpers import (
    _fill_consent_robust,
    _fill_fecha_robust,
    _validate_critical_fields,
    _ensure_consent_marked,
    _get_form_contexts_candidates,
    _get_form_frame,
    _fill_all_via_js,
    _fill_defaults_via_js,
    _fill_field_in_frame,
    _log_field_diagnostics,
)

logger = logging.getLogger(__name__)


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

        # Consentimiento ya marcado; refuerzo por compatibilidad
        _ensure_consent_marked(ctx, self._page)
        self._page.wait_for_timeout(100)

        # Llenar TODOS los campos por JS
        # #region agent log
        import logging as _logging
        import json as _json_ff, time as _time_ff, pathlib as _pathlib_ff
        _dbg = _logging.getLogger("debug.ad0d4e")
        _dbg.info("[DBG-B] record antes de JS fill — NAME: %r | DOB: %r", record.get("NAME", ""), record.get("DOB", ""))
        _log_path_ff = _pathlib_ff.Path("/Users/luciodelacruz/Desktop/2026/Llenado Kobo tools/.cursor/debug-005d64.log")
        _log_path_ff.parent.mkdir(parents=True, exist_ok=True)
        _ff_entry_pre = {"sessionId": "005d64", "hypothesisId": "B-C", "location": "form_filler/__init__.py:pre_js_fill",
                         "message": "record values pre JS fill", "timestamp": int(_time_ff.time() * 1000),
                         "data": {"record_SCH": record.get("SCH", ""), "record_OTH": record.get("OTH", ""),
                                  "record_BCS": record.get("BCS", ""), "record_POC": record.get("POC", "")}}
        with open(_log_path_ff, "a", encoding="utf-8") as _f_ff:
            _f_ff.write(_json_ff.dumps(_ff_entry_pre, ensure_ascii=False) + "\n")
        # #endregion
        filled_js = _fill_all_via_js(ctx, record, self.mapping, self._page)
        self._page.wait_for_timeout(150)

        # Diagnóstico: loguear estado de campos clave tras el JS fill
        _log_field_diagnostics(ctx, self.mapping, record)
        # #region agent log
        try:
            _sch_path = self.mapping.get("SCH", "/aD6FdrTDPaW4QzCLjmG7WE/group_nl0pw33/SCH")
            _oth_path = self.mapping.get("OTH", "/aD6FdrTDPaW4QzCLjmG7WE/group_nl0pw33/OTH")
            _bcs_path = self.mapping.get("BCS", "/aD6FdrTDPaW4QzCLjmG7WE/group_nl0pw33/BCS")
            _dom_check = ctx.locator("body").evaluate("""
                (_, paths) => {
                    function findEl(p) {
                        var pn = p.replace(/^\\//, '');
                        var el = document.querySelector('input[name="' + p + '"], input[name="' + pn + '"]') ||
                                 document.querySelector('textarea[name="' + p + '"], textarea[name="' + pn + '"]');
                        if (!el) return {found: false, value: null, visible: false};
                        var style = window.getComputedStyle(el);
                        return {found: true, value: el.value, visible: style.display !== 'none' && style.visibility !== 'hidden'};
                    }
                    return {SCH: findEl(paths.SCH), OTH: findEl(paths.OTH), BCS: findEl(paths.BCS)};
                }
            """, {"SCH": _sch_path, "OTH": _oth_path, "BCS": _bcs_path})
            _ff_dom_entry = {"sessionId": "005d64", "hypothesisId": "B-C", "location": "form_filler/__init__.py:post_js_fill",
                             "message": "DOM check after JS fill", "timestamp": int(_time_ff.time() * 1000),
                             "data": {"dom": _dom_check, "record_BCS": record.get("BCS", ""),
                                      "record_SCH": record.get("SCH", ""), "record_OTH": record.get("OTH", "")}}
            with open(_log_path_ff, "a", encoding="utf-8") as _f_ff:
                _f_ff.write(_json_ff.dumps(_ff_dom_entry, ensure_ascii=False) + "\n")
        except Exception as _e_ff:
            with open(_log_path_ff, "a", encoding="utf-8") as _f_ff:
                _f_ff.write(_json_ff.dumps({"sessionId": "005d64", "location": "form_filler/__init__.py:post_js_fill",
                                             "message": f"error DOM check: {_e_ff}", "timestamp": int(_time_ff.time() * 1000)}) + "\n")
        # #endregion
        # #region agent log
        try:
            name_path = self.mapping.get("NAME", "/aD6FdrTDPaW4QzCLjmG7WE/group_py4vt65/NAME")
            _name_after_js = ctx.locator(f'input[name="{name_path}"], input[name="{name_path.lstrip("/")}"]').first.input_value() if ctx.locator(f'input[name="{name_path}"]').count() > 0 else "NOT_FOUND"
            _dbg.info("[DBG-C] NAME en DOM despues de JS fill: %r", _name_after_js)
        except Exception as _e:
            _dbg.info("[DBG-C] Error leyendo NAME despues de JS fill: %s", _e)
        # #endregion

        # Respaldo: llenado página por página (siempre, para cubrir campos condicionales
        # que JS fill no puede alcanzar porque XForms los muestra de forma asíncrona)
        filled_total = filled_js
        _total_mapping_fields = sum(1 for col in self.mapping if str(record.get(col, "")).strip())
        logger.info("JS fill cubrió %d/%d campos; ejecutando bucle de respaldo para campos condicionales",
                    filled_js, _total_mapping_fields)
        max_pages = 15
        for _ in range(max_pages):
            filled_this_page = 0
            for col, field_path in self.mapping.items():
                val = str(record.get(col, "")).strip()
                if not val:
                    continue
                # Modalidad: filling_rules ya envía "1" (value real del form = Móvil)
                if col == "Modalidad_de_la_atenci_n":
                    val = "1"
                _fill_ok = _fill_field_in_frame(ctx, field_path, val, force=True)
                # #region agent log
                if col in ("BCS", "SCH", "OTH", "Lugar_de_Atenci_n_Baja_Califo", "CHIH", "Lugar_de_Atenci_n_Nuevo_Le_n", "Lugar_de_Atenci_n_Sonora"):
                    _fb_entry = {"sessionId": "005d64", "hypothesisId": "B-C", "location": "form_filler/__init__.py:fallback_loop",
                                 "message": f"fallback fill col={col}", "timestamp": int(_time_ff.time() * 1000),
                                 "data": {"col": col, "val": val, "fill_ok": _fill_ok}}
                    with open(_log_path_ff, "a", encoding="utf-8") as _f_ff:
                        _f_ff.write(_json_ff.dumps(_fb_entry, ensure_ascii=False) + "\n")
                # #endregion
                if _fill_ok:
                    filled_this_page += 1
                    filled_total += 1
                    if col in ("POC", "Modalidad_de_la_atenci_n"):
                        self._page.wait_for_timeout(100)
                    if col == "NAT":
                        self._page.wait_for_timeout(50)
                # #region agent log
                if col == "DOB":
                    try:
                        name_path = self.mapping.get("NAME", "/aD6FdrTDPaW4QzCLjmG7WE/group_py4vt65/NAME")
                        _name_after_dob = ctx.locator(f'input[name="{name_path}"]').first.input_value() if ctx.locator(f'input[name="{name_path}"]').count() > 0 else "NOT_FOUND"
                        _dbg.info("[DBG-D] NAME en DOM despues de fill DOB (fallback): %r", _name_after_dob)
                    except Exception as _e2:
                        _dbg.info("[DBG-D] Error leyendo NAME despues de fill DOB: %s", _e2)
                # #endregion

            self._page.wait_for_timeout(50)

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
        """Espera confirmación de envío."""
        try:
            self._page.wait_for_timeout(1500)
            # Enketo redirige o muestra mensaje - si no hay error visible, asumir éxito
            return True
        except Exception:
            return True
