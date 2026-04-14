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
import tempfile
import threading
from datetime import datetime
import shutil
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
from file_store import (
    PENDING_DIR,
    VALIDATED_DIR,
    add_file_record,
    delete_file_record,
    ensure_validated_location,
    get_file_path,
    get_file_record,
    init_files_db,
    list_file_records,
    mark_file_validated,
)

# Coordenadas por defecto para Vizcaíno, BCS
_VIZCAINO_LAT = "27.600992342277443"
_VIZCAINO_LON = "-113.57458248245227"

# Coordenadas para Obregón (Colegio del Pacífico)
_OBREGON_LAT = "27.001378831820958"
_OBREGON_LON = "-109.5292450414848"
_OBREGON_LUGAR = "Colegio del Pacifico"
_OBREGON_ESTADO = "Sonora"

# Coordenadas para UPS (Montemorelos)
_UPS_LAT = "25.189316843917055"
_UPS_LON = "-99.83827676024708"
_UPS_LUGAR = "Montemorelos"
_UPS_ESTADO = "Nuevo León"

# Coordenadas para Feria de Salud Plomo / CD. Juárez
_FERIA_LAT = "31.738845221464400"
_FERIA_LON = "-106.49676559838672"
_FERIA_LUGAR = "Ciudad Juárez"
_FERIA_ESTADO = "Chihuahua"

# Estados válidos para Lugar de atención
_ESTADOS_VALIDOS_LUGAR = {
    "baja california", "baja california sur", "sonora",
    "nuevo leon", "nuevo león", "chihuahua",
}


def _normalize_for_match(s: str) -> str:
    import unicodedata as _ud
    s = _ud.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not _ud.combining(ch))
    return s.lower().strip()


def _is_vizcaino(lugar: str) -> bool:
    return "vizcaino" in _normalize_for_match(lugar)


def _is_obregon(filename: str) -> bool:
    n = _normalize_for_match(filename)
    return "obregon" in n or "obregón" in (filename or "").lower()


def _is_ups(filename: str) -> bool:
    import re
    n = _normalize_for_match(filename)
    return bool(re.search(r'(?:^|[\s_\-])ups(?:[\s_\-.]|$)', n))


def _is_feria_plomo(filename: str) -> bool:
    n = _normalize_for_match(filename)
    return "feria" in n and "plomo" in n


def _detect_lugar_from_column(records: list[dict]) -> tuple[str, str, str, str] | None:
    """Busca en las columnas Lugar / Estado_brigada un estado válido para asignar ubicación."""
    for rec in records[:5]:
        for field in ("Lugar", "Estado_brigada"):
            val = _normalize_for_match(str(rec.get(field, "")))
            if val:
                for est in _ESTADOS_VALIDOS_LUGAR:
                    if est in val:
                        return None  # hay estado válido, dejar que filling_rules lo resuelva
    return None

STATIC_DIR = PROJECT_ROOT / "static"
app = Flask(__name__, static_folder=str(STATIC_DIR))
CORS(app)

UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv", "pdf"}
MAX_UPLOAD_MB = 25  # Límite de tamaño para subidas manuales (MB)

# Inicializar DB ligera para gestión de archivos compartidos
init_files_db()

# Cola de progreso para SSE (se rellena desde el thread del runner)
progress_queue: Queue = Queue()
# Lista de eventos de progreso indexada (para reconexiones SSE sin pérdida)
progress_events: list[dict] = []
progress_events_lock = threading.Lock()
progress_event_notify = threading.Condition()


def _push_progress_event(evt: dict):
    """Agrega evento a la lista indexada y notifica a los generadores SSE."""
    with progress_events_lock:
        progress_events.append(evt)
    with progress_event_notify:
        progress_event_notify.notify_all()


def _try_auto_mark_koboup(filename: str | None):
    """Compatibilidad retroactiva.

    El estado confiable de KoboUp ya no depende de marcas locales, sino del
    historial real de cargas exitosas por nombre original. Esta función se
    mantiene como no-op para no romper llamadas existentes.
    """
    return
# Ruta del Excel actual (subido por el usuario)
current_excel_path: Path | None = None
# Ruta del PDF actual (si se subió PDF)
current_pdf_path: Path | None = None
# Nombre original del archivo tal como lo subió el usuario (preserva el nombre real)
current_original_filename: str | None = None
# Estado: "idle" | "running"
run_status = {"status": "idle"}
run_lock = threading.Lock()
# Subproceso (Gunicorn) o evento (local) para la carga en curso
carga_subprocess: subprocess.Popen | None = None
carga_stop_path: str | None = None
# Evento para detener la carga en modo thread (local)
stop_event = threading.Event()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _augment_file_entry(entry: dict) -> dict:
    """Agrega URLs derivadas para el frontend."""
    if not entry:
        return entry
    entry = dict(entry)
    file_id = entry.get("id")
    if file_id is not None:
        entry["download_url"] = f"/api/files/{file_id}/download"
    return entry


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
    global current_excel_path, current_pdf_path, current_original_filename
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "Solo se permiten .xlsx, .xls, .csv o .pdf"}), 400
    ext = f.filename.rsplit(".", 1)[1].lower()
    original_name = f.filename  # Nombre real que subió el usuario
    safe_name = secure_filename(f.filename)
    if not safe_name:
        safe_name = f"archivo.{ext}"
    path = UPLOAD_DIR / safe_name
    f.save(str(path))
    current_original_filename = original_name
    if ext == "pdf":
        current_pdf_path = path
        current_excel_path = None
        return jsonify({"ok": True, "filename": safe_name, "original_filename": original_name, "type": "pdf"})
    else:
        current_excel_path = path
        current_pdf_path = None
        return jsonify({"ok": True, "filename": safe_name, "original_filename": original_name, "type": "excel"})


def _normalize_name(name: str) -> str:
    """Normaliza un nombre para comparación: minúsculas, sin acentos, sin espacios extra."""
    import unicodedata as _ud
    s = _ud.normalize("NFKD", str(name or "").strip())
    s = "".join(ch for ch in s if not _ud.combining(ch))
    return " ".join(s.lower().split())


def _build_cross_validation(
    records: list[dict],
    already_submitted: list[int],
    store: dict,
) -> dict:
    """Compara pacientes del archivo contra historial de envíos previos."""
    submitted_set = set(already_submitted)
    submissions = store.get("submissions", [])
    prev_names: dict[str, list[dict]] = {}
    for sub in submissions:
        norm = _normalize_name(sub.get("name", ""))
        if norm:
            prev_names.setdefault(norm, []).append(sub)

    exact_dupes = []
    possible_dupes = []
    new_indices = []

    for i, rec in enumerate(records):
        if i in submitted_set:
            exact_dupes.append(i)
            continue
        name = _normalize_name(rec.get("NAME", ""))
        if name and name in prev_names:
            matches = prev_names[name]
            possible_dupes.append({
                "index": i,
                "name": rec.get("NAME", ""),
                "matched_with": [
                    {
                        "name": m.get("name", ""),
                        "file": m.get("file", ""),
                        "date": m.get("date", "")[:10],
                        "service": m.get("service", ""),
                    }
                    for m in matches[:3]
                ],
            })
        else:
            new_indices.append(i)

    return {
        "exact_duplicates": exact_dupes,
        "possible_duplicates": possible_dupes,
        "new_records": new_indices,
        "summary": {
            "total": len(records),
            "already_loaded": len(exact_dupes),
            "possible_dupes": len(possible_dupes),
            "new": len(new_indices),
        },
    }


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
        fname = current_original_filename or (current_excel_path.name if current_excel_path else "")

        # ── Detección automática por nombre de archivo ───────────────────────
        if _is_obregon(fname):
            defaults["Estado_brigada"] = _OBREGON_ESTADO
            defaults["Lugar"] = _OBREGON_LUGAR
            defaults["Latitud"] = _OBREGON_LAT
            defaults["Longitud"] = _OBREGON_LON
            defaults["Ubicacion_geografica"] = f"{_OBREGON_LAT} {_OBREGON_LON} 0 0"
            coords_from_store = _OBREGON_LUGAR
        elif _is_ups(fname):
            defaults["Estado_brigada"] = _UPS_ESTADO
            defaults["Lugar"] = _UPS_LUGAR
            defaults["Latitud"] = _UPS_LAT
            defaults["Longitud"] = _UPS_LON
            defaults["Ubicacion_geografica"] = f"{_UPS_LAT} {_UPS_LON} 0 0"
            coords_from_store = _UPS_LUGAR
        elif _is_feria_plomo(fname):
            defaults["Estado_brigada"] = _FERIA_ESTADO
            defaults["Lugar"] = _FERIA_LUGAR
            defaults["Latitud"] = _FERIA_LAT
            defaults["Longitud"] = _FERIA_LON
            defaults["Ubicacion_geografica"] = f"{_FERIA_LAT} {_FERIA_LON} 0 0"
            coords_from_store = _FERIA_LUGAR
        else:
            # ── Leer defaults desde los datos del Excel ──────────────────────
            if str(first.get("Estado_brigada", "")).strip():
                defaults["Estado_brigada"] = str(first["Estado_brigada"]).strip()
            if str(first.get("Lugar", "")).strip():
                defaults["Lugar"] = str(first["Lugar"]).strip()

            # Coordenadas explícitas en el Excel
            lat_first = str(first.get("Latitud", first.get("lat", ""))).strip()
            lon_first = str(first.get("Longitud", first.get("long", ""))).strip()
            if lat_first and lon_first:
                defaults["Latitud"] = lat_first
                defaults["Longitud"] = lon_first
                defaults["Ubicacion_geografica"] = f"{lat_first} {lon_first} 0 0"
            else:
                coords_raw = str(first.get("Ubicacion_geografica", first.get("Coordenadas", ""))).strip()
                if coords_raw:
                    lat_p, lon_p, alt_p, acc_p = parse_coords_string(coords_raw)
                    if lat_p and lon_p:
                        defaults["Latitud"] = lat_p
                        defaults["Longitud"] = lon_p
                        defaults["Ubicacion_geografica"] = f"{lat_p} {lon_p} {alt_p or '0'} {acc_p or '0'}".strip()

            # ── Validar Lugar de atención de las columnas del Excel ──────────
            lugar_default = defaults.get("Lugar", "")
            estado_default = defaults.get("Estado_brigada", "")
            lugar_or_estado = _normalize_for_match(lugar_default or estado_default)

            has_valid_lugar = any(est in lugar_or_estado for est in _ESTADOS_VALIDOS_LUGAR)

            if not has_valid_lugar and lugar_default:
                if _is_vizcaino(lugar_default):
                    has_valid_lugar = True

            if has_valid_lugar and (not defaults.get("Latitud") or not defaults.get("Longitud")):
                if _is_vizcaino(lugar_default or estado_default):
                    defaults["Latitud"] = _VIZCAINO_LAT
                    defaults["Longitud"] = _VIZCAINO_LON
                    defaults["Ubicacion_geografica"] = f"{_VIZCAINO_LAT} {_VIZCAINO_LON} 0 0"
                    coords_from_store = lugar_default or estado_default
                else:
                    stored = get_coords_for_lugar(lugar_default) if lugar_default else None
                    if stored:
                        defaults["Latitud"] = defaults.get("Latitud") or stored.get("lat")
                        defaults["Longitud"] = defaults.get("Longitud") or stored.get("lon")
                        defaults["Ubicacion_geografica"] = coords_to_string(stored)
                        coords_from_store = lugar_default

            if not has_valid_lugar:
                defaults.pop("Estado_brigada", None)
                defaults.pop("Lugar", None)
                defaults.pop("Latitud", None)
                defaults.pop("Longitud", None)
                defaults.pop("Ubicacion_geografica", None)

        # Determinar si las coordenadas son obligatorias (lugar no reconocido y sin coords)
        has_coords = bool(defaults.get("Latitud") and defaults.get("Longitud"))
        coords_required = not has_coords and bool(defaults.get("Lugar"))

        # Validación de datos
        validation = validate_records(records)
        # Identificar filas ya enviadas previamente
        from submitted_tracker import find_submitted_indices, _load_store
        already_submitted = find_submitted_indices(records)

        # Validación cruzada: buscar posibles duplicados por nombre
        cross_validation = _build_cross_validation(records, already_submitted, _load_store())

        return jsonify({
            "ok": True,
            "records": records,
            "count": len(records),
            "defaults": defaults,
            "coords_from_store": coords_from_store,
            "coords_required": coords_required,
            "validation": validation,
            "already_submitted": already_submitted,
            "cross_validation": cross_validation,
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
        # Copia con nombre único en uploads/ para poder recargar el archivo correcto
        safe_stem = secure_filename((current_original_filename or current_pdf_path.stem).rsplit(".", 1)[0]) or "pdf_extract"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        excel_name = f"{safe_stem}_extraido_{timestamp}.xlsx"
        excel_path = UPLOAD_DIR / excel_name
        try:
            if OUT_XLSX.exists():
                shutil.copy(OUT_XLSX, excel_path)
                current_excel_path = excel_path
            else:
                current_excel_path = OUT_XLSX
        except Exception:
            current_excel_path = OUT_XLSX
        return jsonify({
            "ok": True,
            "records": records,
            "count": len(records),
            "backend": backend,
            "excel_filename": current_excel_path.name,
            "excel_path": str(current_excel_path),
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
        # Guardar con nombre único para que cada recarga apunte a su archivo
        base_name = secure_filename((current_original_filename or "datos_extraidos").rsplit(".", 1)[0]) or "datos_extraidos"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{base_name}_verificado_{timestamp}.xlsx"
        out_path = UPLOAD_DIR / filename
        df.to_excel(out_path, index=False, engine="openpyxl")
        current_excel_path = out_path
        current_pdf_path = None
        return jsonify({
            "ok": True,
            "filename": filename,
            "rows": len(records),
        })
    except Exception as e:
        logging.exception("Error al guardar registros")
        return jsonify({"error": str(e)}), 500


@app.route("/api/open-app", methods=["POST"])
def open_app():
    """Abre la ventana de carga (Playwright). Hazlo PRIMERO; luego sube Excel e Iniciar."""
    try:
        # En Railway/Gunicorn, Playwright sync en el hilo de la petición choca con asyncio (gthread).
        if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
            return jsonify({
                "ok": True,
                "message": "En el servidor no hay ventana de escritorio. Usa «Iniciar carga»; el navegador corre en segundo plano (headless).",
            })
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

    use_subprocess = "gunicorn" in sys.modules

    if use_subprocess:
        _start_via_subprocess(
            current_excel_path, wait_for_confirm, auto_open_window,
            open_form_in_page, use_api, defaults, row_indices, start_row,
            current_original_filename,
        )
    else:
        _start_via_thread(
            current_excel_path, wait_for_confirm, auto_open_window,
            open_form_in_page, use_api, defaults, row_indices, start_row,
            current_original_filename,
        )
    return jsonify({
        "ok": True,
        "message": "Carga iniciada. Observa el progreso abajo." + (
            " Valida cada fila en el formulario." if wait_for_confirm else " Envío automático."
        ),
    })


def _start_via_thread(
    excel_path, wait_for_confirm, auto_open_window,
    open_form_in_page, use_api, defaults, row_indices, start_row,
    original_filename=None,
):
    """Modo local (Flask dev server): thread que comparte browser en memoria."""
    stop_event.clear()

    def run():
        from runner import run_carga
        from shared_browser import get_shared_page, set_shared_page, clear_shared
        from form_filler import FormFiller

        while not progress_queue.empty():
            try:
                progress_queue.get_nowait()
            except Empty:
                break
        with progress_events_lock:
            progress_events.clear()

        _thread_pw = _thread_browser = _thread_context = None
        if not use_api and auto_open_window:
            use_headless = open_form_in_page and not wait_for_confirm
            try:
                existing = get_shared_page()
                if existing:
                    try:
                        existing.evaluate("1")
                    except Exception:
                        existing = None
                        clear_shared()
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
                            filler_temp._page, filler_temp._playwright,
                            filler_temp._browser, filler_temp._context,
                        )
                        _thread_pw = filler_temp._playwright
                        _thread_browser = filler_temp._browser
                        _thread_context = filler_temp._context
                        _push_progress_event({
                            "event": "browser_ready",
                            "message": "Ventana abierta automáticamente." if not use_headless
                            else "Formulario en el panel derecho. Llenado en segundo plano.",
                        })
            except Exception as e:
                _push_progress_event({"event": "info", "message": f"No se pudo abrir navegador: {e}"})

        with run_lock:
            run_status["status"] = "running"
        try:
            def on_progress(evt: dict):
                _push_progress_event(evt)
            run_headless = open_form_in_page and not wait_for_confirm
            run_carga(
                excel_path=excel_path,
                progress_callback=on_progress,
                headless=run_headless,
                start_row=start_row,
                wait_for_user_confirm=wait_for_confirm,
                defaults=defaults,
                row_indices=row_indices,
                use_api=use_api,
                stop_event=stop_event,
                original_filename=original_filename,
            )
        except Exception as e:
            _push_progress_event({"event": "error", "message": str(e)})
        finally:
            clear_shared()
            for _closeable in (_thread_context, _thread_browser):
                try:
                    if _closeable:
                        _closeable.close()
                except Exception:
                    pass
            try:
                if _thread_pw:
                    _thread_pw.stop()
            except Exception:
                pass
            _try_auto_mark_koboup(original_filename)
            with run_lock:
                run_status["status"] = "idle"

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()


def _start_via_subprocess(
    excel_path, wait_for_confirm, auto_open_window,
    open_form_in_page, use_api, defaults, row_indices, start_row,
    original_filename=None,
):
    """Modo Gunicorn/Railway: subprocess aislado sin asyncio."""
    global carga_subprocess, carga_stop_path

    while not progress_queue.empty():
        try:
            progress_queue.get_nowait()
        except Empty:
            break
    with progress_events_lock:
        progress_events.clear()

    fd_confirm, confirm_path = tempfile.mkstemp(prefix="kobo_confirm_", suffix=".txt", text=True)
    os.close(fd_confirm)
    fd_stop, stop_path = tempfile.mkstemp(prefix="kobo_stop_", suffix=".flag", text=True)
    os.close(fd_stop)
    try:
        Path(stop_path).unlink(missing_ok=True)
    except OSError:
        pass

    os.environ["KOBO_CONFIRM_FILE"] = confirm_path

    job = {
        "confirm_file": confirm_path,
        "stop_file": stop_path,
        "excel_path": str(excel_path),
        "wait_for_confirm": wait_for_confirm,
        "auto_open_window": auto_open_window,
        "open_form_in_page": open_form_in_page,
        "use_api": use_api,
        "defaults": defaults,
        "row_indices": row_indices,
        "start_row": start_row,
        "original_filename": original_filename,
    }

    fd_job, job_path = tempfile.mkstemp(prefix="kobo_job_", suffix=".json", text=True)
    with os.fdopen(fd_job, "w", encoding="utf-8") as jf:
        json.dump(job, jf, ensure_ascii=False)

    env = os.environ.copy()
    carga_stop_path = stop_path
    carga_subprocess = subprocess.Popen(
        [sys.executable, "-m", "runner_worker", job_path],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        bufsize=1,
    )
    with run_lock:
        run_status["status"] = "running"

    def drain_and_finalize() -> None:
        global carga_subprocess, carga_stop_path
        proc = carga_subprocess
        try:
            if proc is None or proc.stdout is None:
                return
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                _push_progress_event(evt)
            try:
                proc.wait(timeout=360)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except Exception:
                    pass
            if proc.returncode not in (0, None):
                err = (proc.stderr.read() if proc.stderr else "") or ""
                err_tail = err[-4000:]
                _push_progress_event({
                    "event": "error",
                    "message": f"El proceso de carga terminó con código {proc.returncode}. {err_tail}",
                })
        except Exception as e:
            _push_progress_event({"event": "error", "message": str(e)})
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except Exception:
                    pass
            os.environ.pop("KOBO_CONFIRM_FILE", None)
            for p in (confirm_path, stop_path, job_path):
                try:
                    Path(p).unlink(missing_ok=True)
                except OSError:
                    pass
            _try_auto_mark_koboup(original_filename)
            with run_lock:
                run_status["status"] = "idle"
            carga_subprocess = None
            carga_stop_path = None

    threading.Thread(target=drain_and_finalize, daemon=True).start()


@app.route("/api/stop", methods=["POST"])
def stop_carga():
    """Señala al proceso de carga que debe detenerse."""
    if carga_stop_path:
        try:
            Path(carga_stop_path).write_text("1", encoding="utf-8")
        except OSError:
            pass
    stop_event.set()
    return jsonify({"ok": True, "message": "Señal de parada enviada. La carga se detendrá al terminar la fila actual."})


@app.route("/api/progress")
def progress_sse():
    """Server-Sent Events: stream de eventos de progreso (con soporte para reconexión)."""
    def generate():
        idx = 0
        # Al reconectar, buscar el último evento con progreso para enviar el estado actual
        with progress_events_lock:
            n = len(progress_events)
            # Buscar el último evento de progreso para enviar como estado inicial
            for i in range(n - 1, -1, -1):
                ev = progress_events[i]
                if ev.get("row") is not None or ev.get("stats") is not None:
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    break
            idx = n  # Solo enviar eventos nuevos a partir de aquí

        while True:
            with progress_event_notify:
                progress_event_notify.wait(timeout=30)
            with progress_events_lock:
                n = len(progress_events)
            if idx >= n:
                yield f"data: {json.dumps({'event': 'ping'})}\n\n"
                continue
            while idx < n:
                with progress_events_lock:
                    evt = progress_events[idx]
                idx += 1
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                if evt.get("event") in ("done", "error"):
                    return
    return app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/reset-status", methods=["POST"])
def reset_status():
    """Resetea el estado si quedó bloqueado en 'running'."""
    global run_status, carga_subprocess, carga_stop_path
    with run_lock:
        run_status["status"] = "idle"
    stop_event.clear()
    if carga_stop_path:
        try:
            Path(carga_stop_path).unlink(missing_ok=True)
        except OSError:
            pass
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

# ── KoboUp Integration ────────────────────────────────────────────────────────

KOBOUP_BASE_URL = "https://www.clinicaadventista.online/koboup/"
KOBOUP_PROGRESS_FILE = LOGS_DIR / "koboup_progress.json"


def _load_koboup_progress() -> dict:
    try:
        if KOBOUP_PROGRESS_FILE.exists():
            return json.loads(KOBOUP_PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"completed": [], "last_fetched": ""}


def _save_koboup_progress(data: dict) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    KOBOUP_PROGRESS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _normalize_koboup_filename(name: str) -> str:
    import re
    import unicodedata as _ud

    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"\.(xlsx|csv|xls)$", "", name)
    nfkd = _ud.normalize("NFKD", name)
    name = "".join(c for c in nfkd if not _ud.combining(c))
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _count_sent_per_koboup_file(koboup_files: list[dict]) -> dict[int, int]:
    """Cuenta envíos exitosos por archivo KoboUp usando solo historial real.

    Usa coincidencia exacta por nombre original normalizado para evitar:
    - falsos positivos entre archivos parecidos
    - contadores arriba del total
    - archivos marcados como completados sin evidencia real
    """
    historial_path = LOGS_DIR / "historial.jsonl"
    sent_by_original: dict[str, int] = {}
    if historial_path.exists():
        try:
            for line in historial_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                original_name = (entry.get("archivo_original") or "").strip()
                ok_count = int(entry.get("exitosos", entry.get("ok", 0)) or 0)
                if not original_name or ok_count <= 0:
                    continue
                norm_name = _normalize_koboup_filename(original_name)
                if not norm_name:
                    continue
                # Usar el mayor exitoso observado por archivo, no la suma de corridas.
                sent_by_original[norm_name] = max(sent_by_original.get(norm_name, 0), ok_count)
        except Exception:
            pass

    result: dict[int, int] = {}
    for kf in koboup_files:
        kid = kf.get("id", 0)
        kname = _normalize_koboup_filename(kf.get("original_name", ""))
        result[kid] = sent_by_original.get(kname, 0)
    return result


@app.route("/api/koboup/files", methods=["GET"])
def koboup_files():
    """Consulta la lista de archivos validados en KoboUp y agrega estado local."""
    import urllib.request
    try:
        api_url = KOBOUP_BASE_URL + "api/files?status=validado"
        req = urllib.request.Request(api_url, headers={"User-Agent": "KoboLocalTool/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            remote = json.loads(resp.read().decode("utf-8"))
        if not remote.get("ok"):
            return jsonify({"error": "KoboUp no respondió correctamente"}), 502
        files = remote.get("files", [])
        sent_counts = _count_sent_per_koboup_file(files)
        for f in files:
            fid = f.get("id", 0)
            total_rows = int(f.get("row_count", 0) or 0)
            sent_count = min(sent_counts.get(fid, 0), total_rows) if total_rows > 0 else sent_counts.get(fid, 0)
            if total_rows > 0 and sent_count >= total_rows:
                local_status = "completed"
                status_source = f"Historial real: {sent_count}/{total_rows} exitosos."
            elif sent_count > 0:
                local_status = "partial"
                status_source = f"Historial real: {sent_count}/{total_rows} exitosos."
            else:
                local_status = "pending"
                status_source = "Sin evidencia real en historial para este nombre exacto."
            f["local_status"] = local_status
            f["sent_count"] = sent_count
            f["status_source"] = status_source
        total = len(files)
        done = sum(1 for f in files if f["local_status"] == "completed")
        return jsonify({
            "ok": True,
            "files": files,
            "total": total,
            "completed": done,
            "pending": total - done,
        })
    except Exception as e:
        return jsonify({"error": f"No se pudo conectar a KoboUp: {e}"}), 502


@app.route("/api/koboup/load-file", methods=["POST"])
def koboup_load_file():
    """Descarga un archivo de KoboUp y lo activa como archivo actual."""
    global current_excel_path, current_original_filename
    import urllib.request
    data = request.get_json() or {}
    download_url = data.get("download_url", "")
    original_name = data.get("original_name", "archivo.xlsx")
    file_id = data.get("file_id", "")
    if not download_url:
        return jsonify({"error": "download_url requerido"}), 400
    try:
        full_url = KOBOUP_BASE_URL + download_url.lstrip("/")
        req = urllib.request.Request(full_url, headers={"User-Agent": "KoboLocalTool/1.0"})
        safe_name = secure_filename(original_name) or "koboup_file.xlsx"
        dest_path = UPLOAD_DIR / safe_name
        counter = 1
        while dest_path.exists():
            stem = dest_path.stem
            dest_path = UPLOAD_DIR / f"{stem}_{counter}{dest_path.suffix}"
            counter += 1
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest_path.write_bytes(resp.read())
        current_excel_path = dest_path
        current_original_filename = original_name
        return jsonify({
            "ok": True,
            "filename": dest_path.name,
            "original_filename": original_name,
            "type": "excel",
            "file_id": file_id,
        })
    except Exception as e:
        return jsonify({"error": f"Error al descargar de KoboUp: {e}"}), 500


@app.route("/api/koboup/mark-done", methods=["POST"])
def koboup_mark_done():
    """Marca un archivo de KoboUp como completado."""
    data = request.get_json() or {}
    file_id = str(data.get("file_id", ""))
    if not file_id:
        return jsonify({"error": "file_id requerido"}), 400
    progress = _load_koboup_progress()
    if file_id not in progress["completed"]:
        progress["completed"].append(file_id)
    _save_koboup_progress(progress)
    return jsonify({"ok": True})


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
    try:
        from runner import load_checkpoint
        cp = load_checkpoint()
        if cp:
            return jsonify({"ok": True, "checkpoint": cp})
    except Exception:
        pass
    return jsonify({"ok": False, "checkpoint": None})


# ── Reload file from uploads ──────────────────────────────────────────────────

@app.route("/api/reload-file", methods=["POST"])
def reload_file():
    """Recarga un archivo previamente subido desde uploads/ como archivo activo."""
    global current_excel_path, current_pdf_path, current_original_filename
    data = request.get_json() or {}
    filename = (data.get("filename") or "").strip()
    original_name = (data.get("original_filename") or filename).strip()
    if not filename:
        return jsonify({"error": "Falta nombre de archivo"}), 400
    safe_name = secure_filename(filename)
    path = UPLOAD_DIR / safe_name
    if not path.exists():
        return jsonify({"error": f"El archivo '{safe_name}' ya no está disponible en el servidor"}), 404
    ext = path.suffix.lower()
    if ext not in (".xlsx", ".xls", ".csv"):
        return jsonify({"error": "Solo se pueden recargar archivos Excel o CSV"}), 400
    current_excel_path = path
    current_pdf_path = None
    current_original_filename = original_name or safe_name
    return jsonify({"ok": True, "filename": safe_name, "original_filename": current_original_filename, "type": "excel"})


# ── Historial ─────────────────────────────────────────────────────────────────

@app.route("/api/historial", methods=["GET"])
def get_historial():
    """Devuelve las últimas N entradas del historial de cargas,
    más un resumen de archivos exitosos con URL de descarga."""
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

    archivos_exitosos = _build_archivos_exitosos(entries)

    return jsonify({
        "ok": True,
        "entries": list(reversed(entries)),
        "archivos_exitosos": archivos_exitosos,
    })


def _load_historial_entries() -> list[dict]:
    """Lee el historial de cargas y retorna sus entradas válidas."""
    from config import LOGS_DIR as LD

    historial_file = LD / "historial.jsonl"
    entries: list[dict] = []
    try:
        if historial_file.exists():
            for line in historial_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return entries


def _compute_kpi_stats() -> dict:
    """Reconstruye KPI leyendo Excel/CSV históricos y deduplicando filas ya enviadas."""
    from excel_loader import load_excel_to_records
    from filling_rules import _KEYWORDS_MEDICAMENTO, _norm_servicio, _norm_str, _tiene_lentes
    from submitted_tracker import _load_store, compute_row_hash

    especialidades_orden = [
        "Medicina General",
        "Dental",
        "Fisioterapia",
        "Oftalmología",
        "Laboratorios",
    ]
    especialidades = {nombre: 0 for nombre in especialidades_orden}
    insumos = {
        "kit_dental": 0,
        "medicamento": 0,
        "lentes": 0,
    }

    store = _load_store()
    submissions = store.get("submissions", [])
    if not submissions:
        return {
            "patients_registered": 0,
            "total_consultations": 0,
            "specialties": [{"key": _norm_str(nombre).replace(" ", "_"), "label": nombre, "count": 0} for nombre in especialidades_orden],
            "supplies": [
                {"key": "kit_dental", "label": "Kit dental", "count": 0},
                {"key": "medicamento", "label": "Medicamento", "count": 0},
                {"key": "lentes", "label": "Lentes", "count": 0},
            ],
            "source_files": 0,
            "historial_entries": len(_load_historial_entries()),
        }

    submitted_hashes = {str(sub.get("hash", "")).strip() for sub in submissions if sub.get("hash")}
    file_names: list[str] = []
    seen_files: set[str] = set()
    for sub in submissions:
        file_name = Path(str(sub.get("file", "")).strip()).name
        if not file_name or file_name in seen_files:
            continue
        seen_files.add(file_name)
        file_names.append(file_name)

    seen_hashes: set[str] = set()
    seen_patients: set[tuple[str, str, str, str]] = set()
    existing_med_keywords = [_norm_str(kw) for kw in _KEYWORDS_MEDICAMENTO if kw]
    kit_keywords = [
        _norm_str("kit dental"),
        _norm_str("cepillo dental"),
        _norm_str("pasta dental"),
        _norm_str("hilo dental"),
    ]

    for file_name in file_names:
        path = UPLOAD_DIR / file_name
        if not path.exists() or path.suffix.lower() not in {".xlsx", ".xls", ".csv"}:
            continue
        try:
            records = load_excel_to_records(path)
        except Exception:
            continue
        for rec in records:
            row_hash = compute_row_hash(rec)
            if row_hash not in submitted_hashes or row_hash in seen_hashes:
                continue
            seen_hashes.add(row_hash)
            patient_key = (
                _norm_str(rec.get("NAME", "")),
                str(rec.get("Fecha_de_atenci_n", "")).strip(),
                _norm_str(rec.get("SEX", "")),
                str(rec.get("AGE", "")).strip(),
            )
            if any(patient_key):
                seen_patients.add(patient_key)

            servicio = _norm_servicio(rec.get("Servicio_que_se_brinda", ""))
            if servicio not in especialidades:
                servicio = "Medicina General"
            especialidades[servicio] += 1

            supply_text = " | ".join(
                str(rec.get(field, "")).strip()
                for field in ("Resultados_Lab_Insumos", "Tratamiento", "Especifique_qu_se_entrega")
                if str(rec.get(field, "")).strip()
            )
            supply_norm = _norm_str(supply_text)

            if supply_norm and any(keyword in supply_norm for keyword in kit_keywords):
                insumos["kit_dental"] += 1
            if supply_norm and any(keyword in supply_norm for keyword in existing_med_keywords):
                insumos["medicamento"] += 1
            if _tiene_lentes(supply_text):
                insumos["lentes"] += 1

    return {
        "patients_registered": len(seen_patients),
        "total_consultations": sum(especialidades.values()),
        "specialties": [
            {"key": _norm_str(nombre).replace(" ", "_"), "label": nombre, "count": especialidades[nombre]}
            for nombre in especialidades_orden
        ],
        "supplies": [
            {"key": "kit_dental", "label": "Kit dental", "count": insumos["kit_dental"]},
            {"key": "medicamento", "label": "Medicamento", "count": insumos["medicamento"]},
            {"key": "lentes", "label": "Lentes", "count": insumos["lentes"]},
        ],
        "source_files": len(file_names),
        "historial_entries": len(_load_historial_entries()),
    }


@app.route("/api/kpis", methods=["GET"])
def get_kpis():
    """Devuelve KPI reconstruidos desde los Excel/CSV con filas únicas ya enviadas."""
    try:
        return jsonify({"ok": True, "kpis": _compute_kpi_stats()})
    except Exception as e:
        logging.exception("Error al calcular KPI")
        return jsonify({"ok": False, "error": str(e)}), 500


def _build_archivos_exitosos(entries: list[dict]) -> list[dict]:
    """Agrupa entradas del historial por nombre de archivo y devuelve
    solo aquellos con al menos 1 fila exitosa, con URL de descarga si
    el archivo aún existe en uploads/."""
    agg: dict[str, dict] = {}
    for e in entries:
        nombre_orig = (e.get("archivo_original") or e.get("archivo") or "").strip()
        nombre_interno = (e.get("archivo") or "").strip()
        if not nombre_orig:
            continue
        if nombre_orig not in agg:
            agg[nombre_orig] = {
                "nombre_original": nombre_orig,
                "archivo_interno": nombre_interno,
                "exitosos": 0,
                "fallidos": 0,
                "total": 0,
                "cargas": 0,
                "ultima_fecha": "",
            }
        a = agg[nombre_orig]
        a["exitosos"] += e.get("exitosos", 0)
        a["fallidos"] += e.get("fallidos", 0)
        a["total"] += e.get("total", 0)
        a["cargas"] += 1
        fecha = e.get("fecha", "")
        if fecha > a["ultima_fecha"]:
            a["ultima_fecha"] = fecha
        if nombre_interno and not a["archivo_interno"]:
            a["archivo_interno"] = nombre_interno

    result = []
    for a in agg.values():
        if a["exitosos"] <= 0:
            continue
        interno = a["archivo_interno"]
        download_url = ""
        file_exists = False
        if interno:
            path = UPLOAD_DIR / interno
            if path.exists():
                file_exists = True
                download_url = f"/api/uploads/{interno}/download"
        a["download_url"] = download_url
        a["file_exists"] = file_exists
        result.append(a)

    result.sort(key=lambda x: x["ultima_fecha"], reverse=True)
    return result


@app.route("/api/uploads/<path:filename>/download", methods=["GET"])
def download_upload_file(filename: str):
    """Descarga un archivo del directorio uploads/."""
    safe = secure_filename(filename)
    path = UPLOAD_DIR / safe
    if not path.exists():
        return jsonify({"error": "Archivo no encontrado"}), 404
    return send_file(str(path), as_attachment=True, download_name=safe)


@app.route("/api/uploads/<path:filename>/preview", methods=["GET"])
def preview_upload_file(filename: str):
    """Lee un archivo Excel/CSV de uploads/ y devuelve headers + filas como JSON."""
    import pandas as pd

    safe = secure_filename(filename)
    path = UPLOAD_DIR / safe
    if not path.exists():
        return jsonify({"error": "Archivo no encontrado"}), 404

    try:
        ext = path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(path, dtype=str, keep_default_na=False)
        else:
            return jsonify({"error": f"Formato no soportado: {ext}"}), 400

        df = df.fillna("")
        max_rows = int(request.args.get("limit", 500))
        truncated = len(df) > max_rows
        headers = list(df.columns)
        rows = df.head(max_rows).values.tolist()

        return jsonify({
            "ok": True,
            "filename": safe,
            "headers": headers,
            "rows": rows,
            "total_rows": len(df),
            "truncated": truncated,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


# ── Gestión simple de archivos (subir/descargar/validar) ────────────────────────


@app.route("/api/files", methods=["GET"])
def list_shared_files():
    """Lista archivos subidos por estado opcional (pendiente/validado)."""
    status = (request.args.get("status") or "").strip().lower()
    status_filter = status if status in ("pendiente", "validado") else None
    files = [_augment_file_entry(f) for f in list_file_records(status_filter)]
    return jsonify({"ok": True, "files": files})


@app.route("/api/files", methods=["POST"])
def upload_shared_file():
    """Sube uno o varios archivos a la bóveda simple (pendientes/validados)."""
    files = request.files.getlist("file")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No se envió ningún archivo"}), 400

    status_param = (request.form.get("status") or request.form.get("mark_validated") or "").strip().lower()
    target_status = "validado" if status_param in ("1", "true", "yes", "on", "validado", "validated") else "pendiente"
    dest_dir = VALIDATED_DIR if target_status == "validado" else PENDING_DIR
    dest_dir.mkdir(exist_ok=True, parents=True)
    notes = (request.form.get("notes") or "").strip() or None

    results = []
    errors = []
    for uploaded in files:
        if uploaded.filename == "":
            continue
        if not allowed_file(uploaded.filename):
            errors.append({"filename": uploaded.filename, "error": "Tipo de archivo no permitido"})
            continue

        ext = uploaded.filename.rsplit(".", 1)[1].lower()
        original_name = uploaded.filename
        safe_name = secure_filename(original_name) or f"archivo.{ext}"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        stored_name = f"{timestamp}_{safe_name}"
        dest_path = dest_dir / stored_name

        try:
            uploaded.save(dest_path)
            size_bytes = dest_path.stat().st_size if dest_path.exists() else None
            if size_bytes and size_bytes > MAX_UPLOAD_MB * 1024 * 1024:
                dest_path.unlink(missing_ok=True)
                errors.append({"filename": original_name, "error": f"Excede {MAX_UPLOAD_MB} MB"})
                continue
            record = add_file_record(
                original_name=original_name,
                stored_name=stored_name,
                file_type="pdf" if ext == "pdf" else "excel",
                status=target_status,
                size_bytes=size_bytes,
                notes=notes,
            )
            results.append(_augment_file_entry(record))
        except Exception as exc:
            errors.append({"filename": original_name, "error": str(exc)})

    if len(results) == 1 and not errors:
        return jsonify({"ok": True, "file": results[0]})
    return jsonify({
        "ok": len(results) > 0,
        "files": results,
        "errors": errors,
        "uploaded": len(results),
        "failed": len(errors),
    })


@app.route("/api/files/<int:file_id>/download", methods=["GET"])
def download_shared_file(file_id: int):
    """Descarga un archivo pendiente o validado."""
    entry = get_file_record(file_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404
    path = get_file_path(entry)
    if not path.exists():
        return jsonify({"error": "El archivo ya no está disponible en el servidor"}), 404
    return send_file(
        str(path),
        as_attachment=True,
        download_name=entry.get("original_name") or entry.get("stored_name"),
    )


@app.route("/api/files/<int:file_id>/validate", methods=["POST"])
def validate_shared_file(file_id: int):
    """Marca un archivo como validado y lo mueve a la carpeta de validados."""
    entry = get_file_record(file_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404

    data = request.get_json(silent=True) or {}
    validated_by = (data.get("validated_by") or "").strip() or None
    notes = (data.get("notes") or "").strip() or None

    ensure_validated_location(entry)
    updated = mark_file_validated(file_id, validated_by=validated_by, notes=notes) or entry
    return jsonify({"ok": True, "file": _augment_file_entry(updated)})


@app.route("/api/files/<int:file_id>", methods=["DELETE"])
def delete_shared_file(file_id: int):
    """Elimina el registro y el archivo físico."""
    entry = get_file_record(file_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404
    path = get_file_path(entry)
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    delete_file_record(file_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s:%(name)s:%(message)s",
        datefmt="%H:%M:%S",
    )
    # Puerto 5001 por defecto: en macOS el 5000 suele estar ocupado por AirPlay
    port = int(os.environ.get("PORT", 5001))
    print(f"\n  Abre: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
