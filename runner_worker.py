"""
Ejecuta run_carga en un proceso hijo (multiprocessing 'spawn').

Evita el error de Playwright: "Sync API inside the asyncio loop" cuando el servidor
corre bajo Gunicorn con worker gthread (hilos con bucle asyncio).
"""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
from typing import Any


def worker_main(job: dict[str, Any], progress_q: multiprocessing.Queue, stop_ev: multiprocessing.Event) -> None:
    os.environ["KOBO_CONFIRM_FILE"] = job["confirm_file"]

    from config import APP_URL, FORM_URL, USE_DIRECT_FORM_URL
    from form_filler import FormFiller
    from runner import run_carga
    from shared_browser import get_shared_page, set_shared_page

    def emit(evt: dict) -> None:
        progress_q.put(evt)

    use_api = bool(job.get("use_api"))
    auto_open_window = bool(job.get("auto_open_window", True))
    wait_for_confirm = bool(job.get("wait_for_confirm", True))
    open_form_in_page = bool(job.get("open_form_in_page", True))

    if not use_api and auto_open_window:
        use_headless = open_form_in_page and not wait_for_confirm
        try:
            existing = get_shared_page()
            if not existing:
                filler_temp = FormFiller()
                filler_temp.start(headless=use_headless)
                if filler_temp._page:
                    initial_url = FORM_URL if USE_DIRECT_FORM_URL else APP_URL
                    filler_temp._page.goto(
                        initial_url,
                        wait_until="networkidle" if USE_DIRECT_FORM_URL else "domcontentloaded",
                        timeout=60000 if USE_DIRECT_FORM_URL else 20000,
                    )
                    set_shared_page(
                        filler_temp._page,
                        filler_temp._playwright,
                        filler_temp._browser,
                        filler_temp._context,
                    )
                    emit({
                        "event": "browser_ready",
                        "message": (
                            "Ventana abierta automáticamente."
                            if not use_headless
                            else "Formulario en el panel derecho. Llenado en segundo plano."
                        ),
                    })
        except Exception as e:
            emit({"event": "info", "message": f"No se pudo abrir navegador: {e}"})

    run_headless = open_form_in_page and not wait_for_confirm
    run_carga(
        excel_path=Path(job["excel_path"]),
        progress_callback=emit,
        headless=run_headless,
        start_row=job.get("start_row"),
        wait_for_user_confirm=wait_for_confirm,
        defaults=job.get("defaults") or {},
        row_indices=job.get("row_indices"),
        use_api=use_api,
        stop_event=stop_ev,
    )
