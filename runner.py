"""
Ejecutor de la carga masiva con callback de progreso para el frontend.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from config import FORM_URL, LOGS_DIR, load_mapping, USE_KOBO_API, KOBO_API_TOKEN, KOBO_ASSET_UID, KOBO_KC_URL
from excel_loader import EXCEL_TO_INTERNAL, load_source_dataframe
from filling_rules import apply_rules
from form_filler import FormFiller
from submitted_tracker import mark_row_submitted

CHECKPOINT_FILE = LOGS_DIR / "checkpoint.json"
HISTORIAL_FILE = LOGS_DIR / "historial.jsonl"


def save_checkpoint(row_index: int, excel_path: Path) -> None:
    """Guarda el índice del último registro procesado."""
    LOGS_DIR.mkdir(exist_ok=True)
    try:
        CHECKPOINT_FILE.write_text(
            json.dumps({
                "last_row": row_index,
                "excel": str(excel_path),
                "ts": datetime.now().isoformat(),
            }),
            encoding="utf-8",
        )
    except Exception:
        pass


def clear_checkpoint() -> None:
    """Elimina el checkpoint al iniciar un nuevo proceso."""
    try:
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
    except Exception:
        pass


def load_checkpoint() -> dict | None:
    """Lee el checkpoint guardado, o None si no existe."""
    try:
        if CHECKPOINT_FILE.exists():
            return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def save_historial(stats: dict, excel_path: Path | None = None) -> None:
    """Agrega una entrada al historial de cargas."""
    LOGS_DIR.mkdir(exist_ok=True)
    try:
        entry = {
            "fecha": datetime.now().isoformat(),
            "total": stats.get("total", 0),
            "exitosos": stats.get("exitosos", 0),
            "fallidos": stats.get("fallidos", 0),
            "tiempo_segundos": stats.get("tiempo_segundos", 0),
            "archivo": excel_path.name if excel_path else "",
        }
        with open(HISTORIAL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


ERROR_LOG_FILE_JSON = LOGS_DIR / "errores_filas.json"
FAILED_EXCEL_FILE = LOGS_DIR / "filas_fallidas.xlsx"


def save_error_log(stats: dict, all_records: list, excel_path: Path | None = None) -> None:
    """
    Escribe un log JSON con las filas fallidas y genera un Excel descargable
    con esas filas para poder relanzarlas directamente.
    """
    from config import ERROR_LOG_FILE
    LOGS_DIR.mkdir(exist_ok=True)
    errores = stats.get("errores", [])
    if not errores:
        return
    try:
        log_data = {
            "fecha": datetime.now().isoformat(),
            "archivo": excel_path.name if excel_path else "",
            "total": stats.get("total", 0),
            "fallidos": len(errores),
            "errores": errores,
        }
        ERROR_LOG_FILE_JSON.write_text(
            json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Log de texto legible (usa ERROR_LOG_FILE para que /api/logs lo muestre)
        lines = [f"[{log_data['fecha']}] Archivo: {log_data['archivo']} — {len(errores)} filas fallidas"]
        for err in errores:
            lines.append(f"  Fila {err.get('fila', '?')}: {err.get('mensaje', '')}")
        ERROR_LOG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass
    # Generar Excel con las filas fallidas para poder relanzarlas
    try:
        failed_indices = {int(e["fila"]) - 1 for e in errores if "fila" in e}
        failed_rows = [all_records[i] for i in sorted(failed_indices) if i < len(all_records)]
        if failed_rows:
            df_failed = pd.DataFrame(failed_rows)
            df_failed.to_excel(FAILED_EXCEL_FILE, index=False, engine="openpyxl")
    except Exception:
        pass


def _normalize_record(record: dict, mapping_keys: set) -> dict:
    """Normaliza las claves del registro para que coincidan con el mapping."""
    normalized = {}
    for excel_key, value in record.items():
        val_str = "" if value is None or (isinstance(value, float) and str(value) == "nan") else str(value).strip()
        if not val_str:
            continue
        internal = EXCEL_TO_INTERNAL.get(str(excel_key).strip())
        if internal:
            normalized[internal] = val_str
        elif str(excel_key).strip() in mapping_keys:
            normalized[str(excel_key).strip()] = val_str
    return normalized


def run_carga(
    excel_path: Path,
    progress_callback: Callable[[dict], None] | None = None,
    headless: bool = False,
    start_row: int | None = None,
    wait_for_user_confirm: bool = True,
    defaults: dict[str, str] | None = None,
    row_indices: list[int] | None = None,
    use_api: bool | None = None,
    stop_event: threading.Event | None = None,
) -> dict:
    """
    Ejecuta la carga fila por fila y notifica progreso.

    Args:
        excel_path: Ruta al archivo Excel.
        progress_callback: Función que recibe dicts con keys: event, row, total, success, message, stats, ...
        headless: Si True, el navegador corre en segundo plano.
        start_row: Fila desde la cual empezar (0-indexed).
        stop_event: threading.Event que, cuando se setea, detiene el proceso.

    Returns:
        Dict con total, exitosos, fallidos, errores, tiempo_segundos.
    """
    mapping = load_mapping()
    if not mapping:
        if progress_callback:
            progress_callback({
                "event": "error",
                "message": "mapping.yaml está vacío. Ejecuta discover_form.py y configura el mapeo.",
            })
        return {"total": 0, "exitosos": 0, "fallidos": 0, "errores": [], "tiempo_segundos": 0}

    if not excel_path.exists():
        if progress_callback:
            progress_callback({"event": "error", "message": f"No se encontró el archivo: {excel_path}"})
        return {"total": 0, "exitosos": 0, "fallidos": 0, "errores": [], "tiempo_segundos": 0}

    # Cargar Excel o CSV y normalizar columnas al mapping
    df = load_source_dataframe(excel_path)
    df = df.fillna("")
    mapping_keys_set = set(mapping.keys())
    all_records = []
    for _, row in df.iterrows():
        rec = {str(c): str(row[c]).strip() if pd.notna(row.get(c)) else "" for c in df.columns}
        all_records.append(_normalize_record(rec, mapping_keys_set))

    total_rows = len(all_records)
    start_from = start_row if start_row is not None else 0
    start_from = min(start_from, total_rows - 1) if total_rows > 0 else 0

    # Si se especifican filas a procesar, solo iterar esas (índices 0-based)
    if row_indices is not None and len(row_indices) > 0:
        row_indices_set = set(int(i) for i in row_indices if 0 <= int(i) < total_rows)
        indices_to_process = sorted(row_indices_set)
    else:
        indices_to_process = list(range(start_from, total_rows))

    stats = {"total": 0, "exitosos": 0, "fallidos": 0, "errores": [], "tiempo_segundos": 0}
    start_time = time.perf_counter()
    mapping_keys = set(mapping.keys())
    use_api_mode = use_api if use_api is not None else USE_KOBO_API

    clear_checkpoint()

    def emit(evt: dict) -> None:
        evt.setdefault("stats", stats)
        if progress_callback:
            progress_callback(evt)

    def is_stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

    if use_api_mode and KOBO_API_TOKEN and KOBO_ASSET_UID:
        from kobo_api import submit_via_api
        emit({"event": "info", "message": "Usando envío por API KoboToolbox (sin navegador)."})
        defaults = defaults or {}
        total_steps = len(indices_to_process)
        for step_zero, row_index in enumerate(indices_to_process):
            if is_stopped():
                emit({"event": "info", "message": "Carga detenida por el usuario.", "stats": dict(stats)})
                break
            current_step = step_zero + 1
            # all_records ya está normalizado; usarlo directamente evita doble normalización
            raw_record = dict(all_records[row_index])
            record = dict(raw_record)
            for k, v in defaults.items():
                if v and not str(record.get(k, "")).strip():
                    record[k] = str(v).strip()
            record = apply_rules(record, on_missing=None)
            stats["total"] += 1

            name_preview = record.get("NAME", "")[:30] or f"fila {row_index + 1}"
            emit({
                "event": "row_start",
                "row": current_step,
                "total": total_steps,
                "excel_row": row_index + 1,
                "message": f"Enviando fila {row_index + 1}/{total_steps}: {name_preview}…",
            })

            ok, msg = False, ""
            # Retry con backoff exponencial: hasta 3 intentos (1s, 2s)
            for attempt in range(3):
                if attempt > 0:
                    wait_secs = 2 ** (attempt - 1)  # 1s, 2s
                    emit({
                        "event": "row_attempt",
                        "row": current_step,
                        "total": total_steps,
                        "attempt": attempt + 1,
                        "message": f"Reintentando fila {row_index + 1} (intento {attempt + 1}/3, espera {wait_secs}s)…",
                    })
                    time.sleep(wait_secs)
                ok, msg = submit_via_api(
                    record, mapping,
                    api_token=KOBO_API_TOKEN,
                    asset_uid=KOBO_ASSET_UID,
                    kc_url=KOBO_KC_URL,
                )
                if ok:
                    break

            save_checkpoint(row_index, excel_path)
            if ok:
                stats["exitosos"] += 1
                mark_row_submitted(raw_record, excel_path.name if excel_path else "")
                emit({
                    "event": "row_done",
                    "row": current_step,
                    "total": total_steps,
                    "excel_row": row_index + 1,
                    "success": True,
                    "message": msg,
                    "stats": dict(stats),
                })
                # Rate limiting: pausa entre envíos para no saturar la API de KoboToolbox
                time.sleep(0.5)
            else:
                stats["fallidos"] += 1
                stats["errores"].append({"fila": row_index + 1, "mensaje": msg})
                emit({
                    "event": "row_done",
                    "row": current_step,
                    "total": total_steps,
                    "excel_row": row_index + 1,
                    "success": False,
                    "message": msg,
                    "stats": dict(stats),
                })

        stats["tiempo_segundos"] = round(time.perf_counter() - start_time, 2)
        save_historial(stats, excel_path)
        save_error_log(stats, all_records, excel_path)
        emit({
            "event": "done",
            "message": f"Proceso finalizado. Exitosos: {stats['exitosos']}, Fallidos: {stats['fallidos']}",
            "stats": stats,
            "has_failed_excel": bool(stats.get("errores")),
        })
        return stats

    filler = FormFiller(mapping=mapping)

    use_shared = False
    try:
        from shared_browser import get_shared_page, clear_shared
        shared_page = get_shared_page()
        use_shared = bool(shared_page)
        if use_shared:
            try:
                shared_page.evaluate("1")
            except Exception:
                clear_shared()
                shared_page = None
                use_shared = False
        if use_shared and shared_page:
            emit({"event": "browser_ready", "message": "Usando ventana abierta. El formulario se llenará ahí."})
            filler.start(reuse_page=shared_page)
        else:
            emit({
                "event": "start",
                "message": "Iniciando navegador...",
                "form_url": FORM_URL,
                "total_rows": total_rows,
            })
            emit({"event": "info", "message": "Sin API configurada: se usa llenado por navegador (puede fallar). Para carga fiable, configura KOBO_API_TOKEN y KOBO_ASSET_UID en .env."})
            filler.start(headless=headless)
            emit({"event": "browser_ready", "message": "Navegador listo. Observa la ventana para ver el llenado."})

        def confirm_fn() -> bool:
            from confirm_state import wait_for_confirm
            return wait_for_confirm(timeout=600)  # 10 min máx por fila

        defaults = defaults or {}
        total_steps = len(indices_to_process)
        for step_zero, row_index in enumerate(indices_to_process):
            if is_stopped():
                emit({"event": "info", "message": "Carga detenida por el usuario.", "stats": dict(stats)})
                break
            current_step = step_zero + 1  # 1-based para progreso "Fila 1 / N"
            # all_records ya está normalizado; usarlo directamente evita doble normalización
            raw_record = dict(all_records[row_index])
            record = dict(raw_record)
            # Aplicar defaults de brigada (Estado, Lugar) si no vienen en el Excel
            for k, v in defaults.items():
                if v and not str(record.get(k, "")).strip():
                    record[k] = str(v).strip()
            # Aplicar reglas de llenado (valores fijos, transformaciones)
            record = apply_rules(record, on_missing=None)
            stats["total"] += 1

            name_preview = record.get("NAME", "")[:30] or f"fila {row_index + 1}"
            emit({
                "event": "row_start",
                "row": current_step,
                "total": total_steps,
                "excel_row": row_index + 1,
                "message": f"Llenando fila {row_index + 1}/{total_steps}: {name_preview}…",
            })

            success = False
            last_error = None
            for attempt in range(2):
                if attempt > 0:
                    wait_secs = 2
                    emit({
                        "event": "row_attempt",
                        "row": current_step,
                        "total": total_steps,
                        "attempt": attempt + 1,
                        "message": f"Reintentando fila {row_index + 1} (intento {attempt + 1}/2, espera {wait_secs}s)…",
                    })
                    time.sleep(wait_secs)
                if is_stopped():
                    break
                try:
                    if wait_for_user_confirm:
                        emit({
                            "event": "waiting_for_confirm",
                            "row": current_step,
                            "total": total_steps,
                            "excel_row": row_index + 1,
                            "record_preview": {k: v for k, v in list(record.items())[:5]},
                        })
                    success = filler.fill_record(
                        record,
                        row_index,
                        wait_for_confirm=wait_for_user_confirm,
                        confirm_callback=confirm_fn if wait_for_user_confirm else None,
                    )
                    if success:
                        stats["exitosos"] += 1
                        save_checkpoint(row_index, excel_path)
                        mark_row_submitted(raw_record, excel_path.name if excel_path else "")
                        emit({
                            "event": "row_done",
                            "row": current_step,
                            "total": total_steps,
                            "excel_row": row_index + 1,
                            "success": True,
                            "message": f"Fila {row_index + 1} enviada correctamente",
                            "stats": dict(stats),
                        })
                        break
                except Exception as e:
                    last_error = str(e)
                    emit({
                        "event": "row_attempt",
                        "row": current_step,
                        "total": total_steps,
                        "attempt": attempt + 1,
                        "message": str(e),
                    })

            if not success and not is_stopped():
                stats["fallidos"] += 1
                err_entry = {"fila": int(row_index) + 1, "mensaje": last_error or "Envío fallido"}
                stats["errores"].append(err_entry)
                save_checkpoint(row_index, excel_path)
                emit({
                    "event": "row_done",
                    "row": current_step,
                    "total": total_steps,
                    "excel_row": row_index + 1,
                    "success": False,
                    "message": last_error or "Fallido",
                    "stats": dict(stats),
                })

    except Exception as e:
        emit({"event": "error", "message": str(e), "stats": stats})
        raise
    finally:
        filler.stop(close_browser=not use_shared)
        stats["tiempo_segundos"] = round(time.perf_counter() - start_time, 2)
        save_historial(stats, excel_path)
        save_error_log(stats, all_records, excel_path)
        emit({
            "event": "done",
            "message": f"Proceso finalizado. Exitosos: {stats['exitosos']}, Fallidos: {stats['fallidos']}",
            "stats": stats,
            "has_failed_excel": bool(stats.get("errores")),
        })

    return stats
