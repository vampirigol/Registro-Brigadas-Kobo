"""
Servidor Flask para el frontend de carga masiva.
- Subir Excel
- Ver configuración (URL, mapeo)
- Iniciar carga y ver progreso en vivo (SSE)
- El navegador se abre en una ventana aparte (headless=False)
"""

import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from queue import Empty, Queue

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from html import escape

from config import APP_URL, FORM_URL, PROJECT_ROOT, LOGS_DIR, load_mapping, USE_DIRECT_FORM_URL
from coords_store import (
    coords_to_string,
    get_coords_for_lugar,
    parse_coords_string,
    upsert_coords_for_lugar,
)

STATIC_DIR = PROJECT_ROOT / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR))
CORS(app)

UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv", "pdf"}

# Cola de progreso para SSE (se rellena desde el thread del runner)
progress_queue: Queue = Queue()
# Ruta del Excel actual (subido por el usuario)
current_excel_path: Path | None = None
# Ruta del PDF actual (si se subió PDF)
current_pdf_path: Path | None = None
# Estado: "idle" | "running"
run_status = {"status": "idle"}
run_lock = threading.Lock()
# Evento para detener la carga en curso
stop_event = threading.Event()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    html_path = STATIC_DIR / "index.html"
    html = html_path.read_text(encoding="utf-8")
    # Inyectar URL del formulario para que el iframe cargue inmediatamente
    html = html.replace(
        'id="formIframe"',
        f'id="formIframe" src="{escape(FORM_URL)}"',
    )
    from flask import Response
    resp = Response(html, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/api/config", methods=["GET"])
def get_config():
    """Devuelve URL del formulario y mapeo actual."""
    from config import USE_KOBO_API
    mapping = load_mapping()
    return jsonify({
        "form_url": FORM_URL,
        "app_url": APP_URL,
        "mapping": mapping,
        "has_mapping": len(mapping) > 0,
        "use_kobo_api": USE_KOBO_API,
        "uploaded_file": current_excel_path.name if current_excel_path else None,
        "uploaded_pdf": current_pdf_path.name if current_pdf_path else None,
    })


@app.route("/api/lugar-coords", methods=["GET"])
def get_lugar_coords():
    """Devuelve coordenadas guardadas para un lugar (persisten entre sesiones)."""
    lugar = (request.args.get("lugar") or "").strip()
    if not lugar:
        return jsonify({"ok": False, "error": "Falta lugar"}), 400
    entry = get_coords_for_lugar(lugar)
    if not entry:
        return jsonify({"ok": False, "found": False})
    return jsonify({
        "ok": True,
        "found": True,
        "coords": {
            "lugar": entry.get("lugar", lugar),
            "lat": entry.get("lat"),
            "lon": entry.get("lon"),
            "alt": entry.get("alt"),
            "acc": entry.get("acc"),
            "source": entry.get("source"),
            "updated_at": entry.get("updated_at"),
            "coords_string": coords_to_string(entry),
        }
    })


@app.route("/api/upload", methods=["POST"])
def upload():
    """Sube Excel o PDF y lo guarda en uploads/."""
    global current_excel_path, current_pdf_path
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "Solo se permiten .xlsx, .xls, .csv o .pdf"}), 400
    ext = f.filename.rsplit(".", 1)[1].lower()
    safe_name = secure_filename(f.filename)
    if not safe_name:
        safe_name = f"archivo.{ext}"
    path = UPLOAD_DIR / safe_name
    f.save(str(path))
    if ext == "pdf":
        current_pdf_path = path
        current_excel_path = None
        return jsonify({"ok": True, "filename": safe_name, "type": "pdf"})
    else:
        current_excel_path = path
        current_pdf_path = None
        return jsonify({"ok": True, "filename": safe_name, "type": "excel"})


@app.route("/api/load-excel", methods=["POST"])
def load_excel():
    """Carga el Excel subido y retorna registros transformados para verificación."""
    global current_excel_path
    if not current_excel_path or not current_excel_path.exists():
        return jsonify({"error": "Sube primero un archivo Excel"}), 400
    try:
        from excel_loader import load_excel_to_records, validate_records

        records = load_excel_to_records(current_excel_path)
        if not records:
            return jsonify({"error": "El Excel no contiene filas o las columnas no coinciden"}), 400
        # Extraer defaults de la primera fila (Estado, Lugar, coords) para prellenar
        first = records[0]
        defaults = {}
        coords_from_store: str | None = None
        if str(first.get("Estado_brigada", "")).strip():
            defaults["Estado_brigada"] = str(first["Estado_brigada"]).strip()
        if str(first.get("Lugar", "")).strip():
            defaults["Lugar"] = str(first["Lugar"]).strip()
        # Coordenadas: buscar columnas Latitud/Longitud explícitas o Ubicacion_geografica
        lat_first = str(first.get("Latitud", "")).strip()
        lon_first = str(first.get("Longitud", "")).strip()
        if lat_first and lon_first:
            defaults["Latitud"] = lat_first
            defaults["Longitud"] = lon_first
        elif str(first.get("Ubicacion_geografica", "")).strip():
            import re as _re
            ubi = str(first["Ubicacion_geografica"]).strip()
            m = _re.match(r"^(-?\d+\.?\d*)\s+(-?\d+\.?\d*)", ubi)
            if m:
                defaults["Latitud"] = m.group(1)
                defaults["Longitud"] = m.group(2)
        # Prefill coordenadas guardadas para este lugar, si el Excel no las trae
        lugar_default = defaults.get("Lugar")
        if lugar_default and (not defaults.get("Latitud") or not defaults.get("Longitud")):
            stored = get_coords_for_lugar(lugar_default)
            if stored:
                defaults["Latitud"] = defaults.get("Latitud") or stored.get("lat")
                defaults["Longitud"] = defaults.get("Longitud") or stored.get("lon")
                # Mantener formato completo para uso posterior
                defaults["Ubicacion_geografica"] = coords_to_string(stored)
                coords_from_store = lugar_default
        # Validación de datos
        validation = validate_records(records)
        return jsonify({
            "ok": True,
            "records": records,
            "count": len(records),
            "defaults": defaults,
            "coords_from_store": coords_from_store,
            "validation": validation,
        })
    except Exception as e:
        logging.exception("Error al cargar Excel")
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract-pdf", methods=["POST"])
def extract_pdf():
    """
    Extrae datos del PDF subido usando la canalización nueva (pdf_extract.py).
    - Genera outputs/pdf_extract.{json,xlsx}
    - Actualiza current_excel_path para que el flujo continúe desde Excel
    """
    global current_pdf_path, current_excel_path
    if not current_pdf_path or not current_pdf_path.exists():
        return jsonify({"error": "Sube primero un archivo PDF"}), 400
    backend = "tesseract"
    if request.is_json:
        backend = request.json.get("backend", "tesseract") or "tesseract"
    try:
        from pdf_extract import extract_pdf_records, OUT_XLSX

        result = extract_pdf_records(current_pdf_path, backend=backend)
        records = result.get("records", [])
        current_excel_path = OUT_XLSX
        return jsonify({
            "ok": True,
            "records": records,
            "count": len(records),
            "backend": backend,
            "excel_filename": OUT_XLSX.name,
            "excel_path": str(OUT_XLSX),
        })
    except Exception as e:
        logging.exception("Error en extracción PDF")
        return jsonify({"error": str(e)}), 500


@app.route("/api/download-extracted-excel", methods=["GET"])
def download_extracted_excel():
    """Descarga el Excel generado por la extracción de PDF."""
    try:
        from pdf_extract import OUT_XLSX
        if not OUT_XLSX.exists():
            return jsonify({"error": "No hay Excel generado"}), 404
        return send_file(OUT_XLSX, as_attachment=True, download_name=OUT_XLSX.name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/use-extracted", methods=["POST"])
def use_extracted():
    """Guarda los registros verificados como Excel y los usa para la carga."""
    global current_excel_path, current_pdf_path
    data = request.get_json()
    if not data or "records" not in data:
        return jsonify({"error": "No se enviaron registros"}), 400
    records = data["records"]
    if not isinstance(records, list) or not records:
        return jsonify({"error": "La lista de registros está vacía"}), 400
    try:
        import pandas as pd
        df = pd.DataFrame(records)
        out_path = UPLOAD_DIR / "datos_extraidos.xlsx"
        df.to_excel(out_path, index=False, engine="openpyxl")
        current_excel_path = out_path
        current_pdf_path = None
        return jsonify({
            "ok": True,
            "filename": "datos_extraidos.xlsx",
            "rows": len(records),
        })
    except Exception as e:
        logging.exception("Error al guardar registros")
        return jsonify({"error": str(e)}), 500


@app.route("/api/open-app", methods=["POST"])
def open_app():
    """Abre la ventana de carga (Playwright). Hazlo PRIMERO; luego sube Excel e Iniciar."""
    try:
        from shared_browser import get_shared_page, set_shared_page
        existing = get_shared_page()
        if existing:
            try:
                existing.bring_to_front()
                initial_url = FORM_URL if USE_DIRECT_FORM_URL else APP_URL
                existing.goto(initial_url, wait_until="networkidle" if USE_DIRECT_FORM_URL else "domcontentloaded", timeout=60000 if USE_DIRECT_FORM_URL else 20000)
                return jsonify({"ok": True, "message": "Ventana ya abierta; enfocada."})
            except Exception:
                pass
        from form_filler import FormFiller
        filler = FormFiller()
        filler.start(headless=False)
        if filler._page:
            initial_url = FORM_URL if USE_DIRECT_FORM_URL else APP_URL
            filler._page.goto(initial_url, wait_until="networkidle" if USE_DIRECT_FORM_URL else "domcontentloaded", timeout=60000 if USE_DIRECT_FORM_URL else 20000)
            set_shared_page(
                filler._page,
                filler._playwright,
                filler._browser,
                filler._context,
            )
            return jsonify({
                "ok": True,
                "message": "Ventana abierta. Usa esa ventana para subir Excel y dar Iniciar.",
            })
        return jsonify({"error": "No se pudo abrir la ventana"}), 500
    except Exception as e:
        logging.exception("Error al abrir ventana")
        return jsonify({"error": str(e)}), 500


@app.route("/api/start", methods=["POST"])
def start():
    """Inicia la carga en un thread; el progreso se envía por SSE."""
    global run_status
    with run_lock:
        if run_status["status"] == "running":
            return jsonify({
                "error": "Ya hay una carga en ejecución. Espera a que termine o recarga la página.",
            }), 409
        if not current_excel_path or not current_excel_path.exists():
            return jsonify({"error": "Sube un archivo Excel primero"}), 400

    mapping = load_mapping()
    if not mapping:
        return jsonify({
            "error": "Configura el mapeo en mapping.yaml (ejecuta discover_form.py y copia a mapping.yaml)",
        }), 400

    data = request.get_json() or {}
    raw_defaults = data.get("defaults") or {}
    defaults = {
        k: v for k, v in raw_defaults.items()
        if k in ("Estado_brigada", "Lugar", "Ubicacion_geografica", "Latitud", "Longitud") and v
    }
    # Si se enviaron Latitud y Longitud como defaults individuales, construir Ubicacion_geografica
    lat_def = str(defaults.get("Latitud", "")).strip()
    lon_def = str(defaults.get("Longitud", "")).strip()
    if lat_def and lon_def and not defaults.get("Ubicacion_geografica"):
        defaults["Ubicacion_geografica"] = f"{lat_def} {lon_def} 0 0"
    wait_for_confirm = data.get("wait_for_confirm", True)
    auto_open_window = data.get("auto_open_window", True)
    open_form_in_page = data.get("open_form_in_page", True)  # Enketo en el iframe del panel derecho
    row_indices = data.get("row_indices")  # None = todas; lista = solo esos índices (0-based)
    use_api = data.get("use_api", False)
    start_row = data.get("start_row")  # Fila inicial para reanudación
    if start_row is not None:
        try:
            start_row = int(start_row)
        except (ValueError, TypeError):
            start_row = None

    # Guardar coordenadas manuales para este lugar (persisten entre sesiones)
    lugar_default = defaults.get("Lugar")
    if lugar_default:
        lat_store = lon_store = alt_store = acc_store = ""
        if lat_def and lon_def:
            lat_store, lon_store, alt_store, acc_store = lat_def, lon_def, "0", "0"
        elif defaults.get("Ubicacion_geografica"):
            lat_store, lon_store, alt_store, acc_store = parse_coords_string(defaults["Ubicacion_geografica"])
        if lat_store and lon_store:
            upsert_coords_for_lugar(
                lugar_default,
                lat_store,
                lon_store,
                alt_store,
                acc_store,
                source="default",
            )

    # Limpiar stop_event antes de iniciar
    stop_event.clear()

    def run():
        from runner import run_carga
        from shared_browser import get_shared_page, set_shared_page
        from form_filler import FormFiller

        while not progress_queue.empty():
            try:
                progress_queue.get_nowait()
            except Empty:
                break

        # Si usamos API no abrimos navegador
        if not use_api and auto_open_window:
            use_headless = open_form_in_page and not wait_for_confirm
            try:
                existing = get_shared_page()
                if not existing:
                    filler_temp = FormFiller()
                    filler_temp.start(headless=use_headless)
                    if filler_temp._page:
                        initial_url = FORM_URL if USE_DIRECT_FORM_URL else APP_URL
                        filler_temp._page.goto(initial_url, wait_until="networkidle" if USE_DIRECT_FORM_URL else "domcontentloaded", timeout=60000 if USE_DIRECT_FORM_URL else 20000)
                        set_shared_page(
                            filler_temp._page,
                            filler_temp._playwright,
                            filler_temp._browser,
                            filler_temp._context,
                        )
                        progress_queue.put({"event": "browser_ready", "message": "Ventana abierta automáticamente." if not use_headless else "Formulario en el panel derecho. Llenado en segundo plano."})
            except Exception as e:
                progress_queue.put({"event": "info", "message": f"No se pudo abrir navegador: {e}"})

        with run_lock:
            run_status["status"] = "running"
        try:
            def on_progress(evt: dict):
                progress_queue.put(evt)
            run_headless = open_form_in_page and not wait_for_confirm
            run_carga(
                excel_path=current_excel_path,
                progress_callback=on_progress,
                headless=run_headless,
                start_row=start_row,
                wait_for_user_confirm=wait_for_confirm,
                defaults=defaults,
                row_indices=row_indices,
                use_api=use_api,
                stop_event=stop_event,
            )
        except Exception as e:
            progress_queue.put({"event": "error", "message": str(e)})
        finally:
            with run_lock:
                run_status["status"] = "idle"

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
    return jsonify({
        "ok": True,
        "message": "Carga iniciada. Observa el progreso abajo." + (
            " Valida cada fila en el formulario." if wait_for_confirm else " Envío automático."
        ),
    })


@app.route("/api/stop", methods=["POST"])
def stop_carga():
    """Señala al proceso de carga que debe detenerse."""
    stop_event.set()
    return jsonify({"ok": True, "message": "Señal de parada enviada. La carga se detendrá al terminar la fila actual."})


@app.route("/api/progress")
def progress_sse():
    """Server-Sent Events: stream de eventos de progreso."""
    def generate():
        while True:
            try:
                evt = progress_queue.get(timeout=60)
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                if evt.get("event") == "done":
                    break
            except Empty:
                yield f"data: {json.dumps({'event': 'ping'})}\n\n"
    return app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/reset-status", methods=["POST"])
def reset_status():
    """Resetea el estado si quedó bloqueado en 'running'."""
    global run_status
    with run_lock:
        run_status["status"] = "idle"
    stop_event.clear()
    return jsonify({"ok": True})


@app.route("/api/confirm-row", methods=["POST"])
def confirm_row():
    """El usuario valida los datos cargados: confirma envío o omite la fila."""
    data = request.get_json() or {}
    action = (data.get("action") or "").strip().lower()
    if action not in ("confirm", "skip"):
        return jsonify({"error": "action debe ser 'confirm' o 'skip'"}), 400
    try:
        from confirm_state import signal_confirm
        signal_confirm(action)
        return jsonify({"ok": True, "action": action})
    except Exception as e:
        logging.exception("Error en confirm-row")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def status():
    return jsonify(run_status)


# ── Logs ──────────────────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Devuelve el contenido de errores.log y estadisticas.json."""
    from config import ERROR_LOG_FILE, STATS_FILE
    error_log = ""
    stats_data = {}
    try:
        if ERROR_LOG_FILE.exists():
            error_log = ERROR_LOG_FILE.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        if STATS_FILE.exists():
            stats_data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return jsonify({"error_log": error_log, "stats": stats_data})


@app.route("/api/logs/download")
def download_logs():
    """Descarga el archivo errores.log."""
    from config import ERROR_LOG_FILE
    if not ERROR_LOG_FILE.exists():
        return jsonify({"error": "No hay log de errores todavía"}), 404
    return send_file(str(ERROR_LOG_FILE), as_attachment=True, download_name="errores.log", mimetype="text/plain")


@app.route("/api/logs/download-failed-excel")
def download_failed_excel():
    """Descarga un Excel con solo las filas que fallaron, listo para relanzar."""
    from runner import FAILED_EXCEL_FILE
    if not FAILED_EXCEL_FILE.exists():
        return jsonify({"error": "No hay filas fallidas registradas"}), 404
    return send_file(
        str(FAILED_EXCEL_FILE),
        as_attachment=True,
        download_name="filas_fallidas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ── Checkpoint ────────────────────────────────────────────────────────────────

@app.route("/api/checkpoint", methods=["GET"])
def get_checkpoint():
    """Devuelve el último checkpoint guardado."""
    from runner import load_checkpoint
    cp = load_checkpoint()
    if cp:
        return jsonify({"ok": True, "checkpoint": cp})
    return jsonify({"ok": False, "checkpoint": None})


# ── Historial ─────────────────────────────────────────────────────────────────

@app.route("/api/historial", methods=["GET"])
def get_historial():
    """Devuelve las últimas N entradas del historial de cargas."""
    from config import LOGS_DIR as LD
    historial_file = LD / "historial.jsonl"
    entries = []
    try:
        if historial_file.exists():
            lines = historial_file.read_text(encoding="utf-8").strip().splitlines()
            for line in lines:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    # Devolver las últimas 20, más recientes primero
    return jsonify({"ok": True, "entries": list(reversed(entries[-20:]))})


# ── Discover form ─────────────────────────────────────────────────────────────

@app.route("/api/discover", methods=["POST"])
def discover_form():
    """Ejecuta discover_form.py y devuelve el mapping generado."""
    discover_script = PROJECT_ROOT / "discover_form.py"
    if not discover_script.exists():
        return jsonify({"error": "No se encontró discover_form.py"}), 404
    try:
        result = subprocess.run(
            [sys.executable, str(discover_script)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
        )
        discovered_path = PROJECT_ROOT / "mapping_discovered.yaml"
        mapping_content = ""
        if discovered_path.exists():
            mapping_content = discovered_path.read_text(encoding="utf-8")
        return jsonify({
            "ok": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "mapping_discovered": mapping_content,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Tiempo de espera agotado al ejecutar discover_form.py (>120s)"}), 504
    except Exception as e:
        logging.exception("Error en discover")
        return jsonify({"error": str(e)}), 500


# ── Mapping editor ────────────────────────────────────────────────────────────

@app.route("/api/mapping", methods=["GET"])
def get_mapping():
    """Devuelve el contenido actual de mapping.yaml."""
    mapping_path = PROJECT_ROOT / "mapping.yaml"
    raw = ""
    try:
        if mapping_path.exists():
            raw = mapping_path.read_text(encoding="utf-8")
    except Exception:
        pass
    mapping = load_mapping()
    return jsonify({"ok": True, "raw": raw, "mapping": mapping})


@app.route("/api/mapping", methods=["POST"])
def save_mapping():
    """Guarda nuevo contenido en mapping.yaml."""
    data = request.get_json() or {}
    raw = data.get("raw", "")
    if not raw and "mapping" in data and isinstance(data["mapping"], dict):
        import yaml
        raw = yaml.dump(data["mapping"], allow_unicode=True, default_flow_style=False)
    if not raw:
        return jsonify({"error": "No se recibió contenido para mapping.yaml"}), 400
    try:
        import yaml
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            return jsonify({"error": "El mapping debe ser un diccionario YAML válido"}), 400
        mapping_path = PROJECT_ROOT / "mapping.yaml"
        mapping_path.write_text(raw, encoding="utf-8")
        return jsonify({"ok": True, "fields": len(parsed)})
    except Exception as e:
        return jsonify({"error": f"YAML inválido: {e}"}), 400


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Puerto 5001 por defecto: en macOS el 5000 suele estar ocupado por AirPlay
    port = int(os.environ.get("PORT", 5001))
    print(f"\n  Abre: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
