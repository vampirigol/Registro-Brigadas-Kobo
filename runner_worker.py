"""
Ejecuta run_carga en un proceso separado (subproceso `python -m runner_worker`).

Evita el error de Playwright: "Sync API inside the asyncio loop" bajo Gunicorn/gthread,
usando un intérprete Python nuevo sin el bucle asyncio del worker WSGI.

También soportaba multiprocessing.spawn; el subproceso es más fiable en Docker/Railway.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Protocol


class ProgressSink(Protocol):
    def put(self, obj: dict) -> None: ...


class StopLike(Protocol):
    def is_set(self) -> bool: ...


class StopFileFlag:
    """Parada cooperativa: el padre crea el fichero al pedir stop."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.unlink(missing_ok=True)

    def is_set(self) -> bool:
        return self._path.exists()


class StdoutProgressSink:
    """Una línea JSON por evento (consumida por el padre vía subprocess.PIPE)."""

    def put(self, evt: dict) -> None:
        print(json.dumps(evt, ensure_ascii=False), flush=True)


def worker_main(job: dict[str, Any], progress_q: ProgressSink, stop_ev: StopLike) -> None:
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


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m runner_worker <ruta_job.json>", file=sys.stderr)
        sys.exit(2)
    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    stop_path = job.get("stop_file")
    if not stop_path:
        print("job.json debe incluir stop_file", file=sys.stderr)
        sys.exit(2)
    stop_ev = StopFileFlag(str(stop_path))
    worker_main(job, StdoutProgressSink(), stop_ev)


if __name__ == "__main__":
    main()
