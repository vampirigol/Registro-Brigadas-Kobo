"""
Servidor Flask independiente para gestión de archivos Excel/PDF.
Subir, descargar, listar y marcar como validados.
"""

import csv
import io
import logging
import os
import re
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from file_store import (
    PENDING_DIR,
    REFERENCES_DIR,
    VALID_STATUSES,
    VALIDATED_DIR,
    add_file_record,
    add_ref_record,
    count_file_rows,
    delete_file_record,
    delete_ref_record,
    ensure_validated_location,
    get_file_path,
    get_file_record,
    get_record_stats,
    get_ref_file_path,
    get_ref_record,
    get_uploader_stats,
    get_validator_stats,
    has_validated_replacement,
    init_files_db,
    list_file_records,
    list_ref_locations,
    list_ref_records,
    mark_file_validated,
    supersede_matching_files,
    supersede_specific_file,
    update_row_count,
    update_status,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
CORS(app)

ALLOWED_EXTENSIONS = {"xlsx", "xls", "csv", "pdf"}
MAX_UPLOAD_MB = 50

init_files_db()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _augment(entry: dict) -> dict:
    if not entry:
        return entry
    entry = dict(entry)
    fid = entry.get("id")
    if fid is not None:
        entry["download_url"] = f"api/files/{fid}/download"
    return entry


def _norm_text(value: str) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _normalize_header(value: str) -> str:
    text = _norm_text(value)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _build_row_dict(headers: list[str], values: list[object]) -> dict[str, str]:
    row: dict[str, str] = {}
    for idx, header in enumerate(headers):
        cell = values[idx] if idx < len(values) else ""
        row[header] = "" if cell is None else str(cell).strip()
    return row


def _load_records_from_file(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        import openpyxl

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        try:
            ws = wb.worksheets[0]
            rows = ws.iter_rows(values_only=True)
            headers_row = next(rows, None)
            if not headers_row:
                return []
            headers = [str(cell).strip() if cell is not None else "" for cell in headers_row]
            return [
                _build_row_dict(headers, list(values))
                for values in rows
                if values and any(cell not in (None, "") for cell in values)
            ]
        finally:
            wb.close()

    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                with open(path, "r", encoding=encoding, errors="replace", newline="") as fh:
                    sample = fh.read(4096)
                    fh.seek(0)
                    try:
                        dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
                    except Exception:
                        dialect = csv.excel
                    reader = csv.reader(fh, dialect)
                    headers = next(reader, None)
                    if not headers:
                        return []
                    headers = [str(cell).strip() if cell is not None else "" for cell in headers]
                    return [
                        _build_row_dict(headers, row)
                        for row in reader
                        if row and any(str(cell).strip() for cell in row)
                    ]
            except Exception:
                continue
    return []


def _pick_value(row: dict[str, str], aliases: list[str]) -> str:
    normalized = {_normalize_header(key): value for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(_normalize_header(alias), "")
        if str(value).strip():
            return str(value).strip()
    return ""


def _normalize_service(raw: str) -> str:
    service_norm = _norm_text(raw)
    alias_map = [
        ("Dental", ["dental", "odontologia", "odontologia"]),
        ("Fisioterapia", ["fisioterapia", "fisio", "rehabilitacion"]),
        ("Oftalmología", ["oftalmologia", "optica", "vision", "lentes"]),
        ("Laboratorios", ["laboratorio", "laboratorios", "lab", "examenes"]),
        ("Medicina General", ["medicina general", "medicina", "consulta", "medico"]),
    ]
    for label, keywords in alias_map:
        if any(keyword in service_norm for keyword in keywords):
            return label
    return "Medicina General"


def _compute_public_kpis() -> dict:
    files = list_file_records("validado")
    specialties_order = [
        "Medicina General",
        "Dental",
        "Fisioterapia",
        "Oftalmología",
        "Laboratorios",
    ]
    specialties = {name: 0 for name in specialties_order}
    supplies = {"kit_dental": 0, "medicamento": 0, "lentes": 0}
    seen_consultations: set[tuple[str, str, str, str, str]] = set()
    seen_patients: set[tuple[str, str, str, str]] = set()

    med_keywords = [
        "medicamento", "medicina", "pastilla", "tableta", "capsula", "capsula",
        "jarabe", "crema", "pomada", "amoxicilina", "ibuprofeno", "paracetamol",
        "omeprazol", "metformina", "insulina", "salbutamol", "albendazol", "vitamina",
    ]
    lens_keywords = ["lentes", "anteojos", "armazon", "armazon", "graduacion", "montura", "bifocal"]
    kit_keywords = ["kit dental", "cepillo dental", "pasta dental", "hilo dental"]

    for file_entry in files:
        path = get_file_path(file_entry)
        if not path.exists() or file_entry.get("file_type") == "pdf":
            continue
        try:
            rows = _load_records_from_file(path)
        except Exception as exc:
            logging.warning("No se pudo leer %s para KPI: %s", path.name, exc)
            continue

        for row in rows:
            name = _pick_value(row, ["NAME", "Nombre del Paciente", "Nombre"])
            date = _pick_value(row, ["Fecha_de_atenci_n", "Fecha de Atención", "Fecha de atención", "Fecha atención", "Fecha"])
            sex = _pick_value(row, ["SEX", "Sexo"])
            age = _pick_value(row, ["AGE", "Edad"])
            service = _pick_value(row, ["Servicio_que_se_brinda", "Servicio que se brinda", "Servicio", "Especialidad"])
            service_label = _normalize_service(service)

            patient_key = (_norm_text(name), date.strip(), _norm_text(sex), age.strip())
            if any(patient_key):
                seen_patients.add(patient_key)

            consultation_key = patient_key + (service_label,)
            if consultation_key in seen_consultations:
                continue
            seen_consultations.add(consultation_key)
            specialties[service_label] += 1

            supply_text = " | ".join(
                part for part in [
                    _pick_value(row, ["Resultados_Lab_Insumos", "Resultados Lab / Insumos", "Insumos Entregados", "Insumos"]),
                    _pick_value(row, ["Tratamiento", "Medicamentos", "Tx"]),
                    _pick_value(row, ["Especifique_qu_se_entrega", "Especifique qué se entrega", "Especifique que se entrega", "Especifique"]),
                ]
                if part
            )
            supply_norm = _norm_text(supply_text)
            if supply_norm and any(keyword in supply_norm for keyword in kit_keywords):
                supplies["kit_dental"] += 1
            if supply_norm and any(keyword in supply_norm for keyword in med_keywords):
                supplies["medicamento"] += 1
            if supply_norm and any(keyword in supply_norm for keyword in lens_keywords):
                supplies["lentes"] += 1

    return {
        "patients_registered": len(seen_patients),
        "total_consultations": sum(specialties.values()),
        "specialties": [
            {"key": _normalize_header(name).replace(" ", "_"), "label": name, "count": specialties[name]}
            for name in specialties_order
        ],
        "supplies": [
            {"key": "kit_dental", "label": "Kit dental", "count": supplies["kit_dental"]},
            {"key": "medicamento", "label": "Medicamento", "count": supplies["medicamento"]},
            {"key": "lentes", "label": "Lentes", "count": supplies["lentes"]},
        ],
        "validated_files": len(files),
    }


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/files", methods=["GET"])
def list_files():
    status = (request.args.get("status") or "").strip().lower()
    status_filter = status if status in VALID_STATUSES else None
    files = [_augment(f) for f in list_file_records(status_filter)]
    return jsonify({"ok": True, "files": files})


@app.route("/api/files", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    uploaded = request.files["file"]
    if uploaded.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    if not allowed_file(uploaded.filename):
        return jsonify({"error": "Solo se permiten .xlsx, .xls, .csv o .pdf"}), 400

    ext = uploaded.filename.rsplit(".", 1)[1].lower()
    original_name = uploaded.filename
    safe_name = secure_filename(original_name) or f"archivo.{ext}"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored_name = f"{timestamp}_{safe_name}"

    uploaded_by = (request.form.get("uploaded_by") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    status_param = (request.form.get("status") or "").strip().lower()
    if status_param in VALID_STATUSES:
        target_status = status_param
    else:
        target_status = "pendiente"

    dest_dir = VALIDATED_DIR if target_status == "validado" else PENDING_DIR
    dest_dir.mkdir(exist_ok=True, parents=True)
    dest_path = dest_dir / stored_name

    uploaded.save(dest_path)
    size_bytes = dest_path.stat().st_size if dest_path.exists() else None

    record = add_file_record(
        original_name=original_name,
        stored_name=stored_name,
        file_type="pdf" if ext == "pdf" else "excel",
        status=target_status,
        size_bytes=size_bytes,
        notes=notes,
        uploaded_by=uploaded_by,
    )

    if ext != "pdf":
        row_count = count_file_rows(dest_path)
        if row_count is not None:
            update_row_count(record["id"], row_count)
            record["row_count"] = row_count

    superseded = []
    if target_status == "validado":
        replaces_id_str = (request.form.get("replaces_id") or "").strip()
        if replaces_id_str:
            try:
                replaces_id = int(replaces_id_str)
                supersede_specific_file(replaces_id, record["id"])
                superseded = [replaces_id]
            except (ValueError, TypeError):
                pass
        if not superseded:
            superseded = supersede_matching_files(record["id"], original_name)

    return jsonify({"ok": True, "file": _augment(record), "superseded": superseded})


@app.route("/api/files/<int:file_id>/download", methods=["GET"])
def download_file(file_id: int):
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


@app.route("/api/files/<int:file_id>/register-download", methods=["POST"])
def register_download(file_id: int):
    """Registra quién descargó y cambia estado a por_validar."""
    entry = get_file_record(file_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404
    data = request.get_json(silent=True) or {}
    downloaded_by = (data.get("downloaded_by") or "").strip() or None

    from file_store import _connect
    from datetime import datetime as _dt
    now = _dt.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE files SET downloaded_by = ?, downloaded_at = ?, updated_at = ? WHERE id = ?",
            (downloaded_by, now, now, file_id),
        )

    if entry.get("status") == "pendiente":
        update_status(file_id, "por_validar")

    updated = get_file_record(file_id)
    return jsonify({"ok": True, "file": _augment(updated)})


@app.route("/api/files/<int:file_id>/status", methods=["POST"])
def change_status(file_id: int):
    """Cambia el estado de un archivo: pendiente → por_validar → validado."""
    entry = get_file_record(file_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404

    if entry.get("status") == "reemplazado":
        return jsonify({"error": "Este archivo ya fue reemplazado y no puede cambiar de estado"}), 409

    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip().lower()
    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"Estado inválido. Use: {', '.join(VALID_STATUSES)}"}), 400

    validated_by = (data.get("validated_by") or "").strip() or None
    notes = (data.get("notes") or "").strip() or None

    if new_status == "validado":
        if has_validated_replacement(file_id):
            update_status(file_id, "reemplazado")
            updated = get_file_record(file_id)
            return jsonify({
                "ok": True,
                "file": _augment(updated),
                "was_superseded": True,
                "message": "Este archivo fue marcado como reemplazado porque ya existe una versión validada.",
            })
        ensure_validated_location(entry)

    updated = update_status(file_id, new_status, validated_by=validated_by, notes=notes)

    superseded = []
    if new_status == "validado":
        superseded = supersede_matching_files(file_id, entry["original_name"])

    return jsonify({"ok": True, "file": _augment(updated), "superseded": superseded})


@app.route("/api/files/<int:file_id>/validate", methods=["POST"])
def validate_file(file_id: int):
    entry = get_file_record(file_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404

    if entry.get("status") == "reemplazado":
        return jsonify({"error": "Este archivo ya fue reemplazado por una versión validada"}), 409

    if has_validated_replacement(file_id):
        update_status(file_id, "reemplazado")
        updated = get_file_record(file_id)
        return jsonify({
            "ok": True,
            "file": _augment(updated),
            "was_superseded": True,
            "message": "Este archivo fue marcado como reemplazado porque ya existe una versión validada.",
        })

    data = request.get_json(silent=True) or {}
    validated_by = (data.get("validated_by") or "").strip() or None
    notes = (data.get("notes") or "").strip() or None
    ensure_validated_location(entry)
    updated = mark_file_validated(file_id, validated_by=validated_by, notes=notes) or entry

    superseded = supersede_matching_files(file_id, entry["original_name"])

    return jsonify({"ok": True, "file": _augment(updated), "superseded": superseded})


@app.route("/api/files/<int:file_id>/replace-with", methods=["POST"])
def replace_with_existing(file_id: int):
    """Marca este archivo como reemplazado por otro archivo ya validado en el sistema."""
    entry = get_file_record(file_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404

    if entry.get("status") == "reemplazado":
        return jsonify({"error": "Este archivo ya fue reemplazado"}), 409

    data = request.get_json(silent=True) or {}
    validated_file_id = data.get("validated_file_id")
    if not validated_file_id:
        return jsonify({"error": "Debes indicar el archivo validado"}), 400

    validated_entry = get_file_record(int(validated_file_id))
    if not validated_entry:
        return jsonify({"error": "El archivo validado seleccionado no existe"}), 404

    if validated_entry.get("status") != "validado":
        return jsonify({"error": "El archivo seleccionado no tiene estado 'validado'"}), 400

    supersede_specific_file(file_id, int(validated_file_id))
    updated = get_file_record(file_id)
    return jsonify({"ok": True, "file": _augment(updated)})


@app.route("/api/files/<int:file_id>", methods=["DELETE"])
def delete_file(file_id: int):
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


# ── Reference PDFs ─────────────────────────────────────────────────


def _augment_ref(entry: dict) -> dict:
    if not entry:
        return entry
    entry = dict(entry)
    rid = entry.get("id")
    if rid is not None:
        entry["download_url"] = f"api/refs/{rid}/download"
    return entry


@app.route("/api/refs", methods=["GET"])
def list_refs():
    location = (request.args.get("location") or "").strip() or None
    refs = [_augment_ref(r) for r in list_ref_records(location)]
    return jsonify({"ok": True, "refs": refs})


@app.route("/api/refs/locations", methods=["GET"])
def get_locations():
    return jsonify({"ok": True, "locations": list_ref_locations()})


@app.route("/api/refs", methods=["POST"])
def upload_ref():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    uploaded = request.files["file"]
    if uploaded.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    if not uploaded.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Solo se permiten archivos PDF"}), 400

    location = (request.form.get("location") or "").strip()
    if not location:
        return jsonify({"error": "La ubicación es obligatoria"}), 400

    original_name = uploaded.filename
    safe_name = secure_filename(original_name) or "referencia.pdf"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored_name = f"{timestamp}_{safe_name}"

    REFERENCES_DIR.mkdir(exist_ok=True, parents=True)
    dest_path = REFERENCES_DIR / stored_name
    uploaded.save(dest_path)
    size_bytes = dest_path.stat().st_size if dest_path.exists() else None

    uploaded_by = (request.form.get("uploaded_by") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    record = add_ref_record(
        original_name=original_name,
        stored_name=stored_name,
        location=location,
        uploaded_by=uploaded_by,
        notes=notes,
        size_bytes=size_bytes,
    )
    return jsonify({"ok": True, "ref": _augment_ref(record)})


@app.route("/api/refs/<int:ref_id>/download", methods=["GET"])
def download_ref(ref_id: int):
    entry = get_ref_record(ref_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404
    path = get_ref_file_path(entry)
    if not path.exists():
        return jsonify({"error": "El archivo ya no está disponible"}), 404
    return send_file(
        str(path),
        as_attachment=True,
        download_name=entry.get("original_name") or entry.get("stored_name"),
    )


@app.route("/api/refs/<int:ref_id>", methods=["DELETE"])
def delete_ref(ref_id: int):
    entry = get_ref_record(ref_id)
    if not entry:
        return jsonify({"error": "Archivo no encontrado"}), 404
    path = get_ref_file_path(entry)
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    delete_ref_record(ref_id)
    return jsonify({"ok": True})


BULK_DOWNLOAD_PASSWORD = "vamoscontodo"


@app.route("/api/files/download-validated-zip", methods=["POST"])
def download_validated_zip():
    """Descarga masiva de todos los archivos validados en un .zip protegido por contraseña."""
    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip()
    if password != BULK_DOWNLOAD_PASSWORD:
        return jsonify({"error": "Contraseña incorrecta"}), 403

    validated = list_file_records("validado")
    if not validated:
        return jsonify({"error": "No hay archivos validados para descargar"}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        seen_names: dict[str, int] = {}
        for entry in validated:
            path = get_file_path(entry)
            if not path.exists():
                continue
            dl_name = entry.get("original_name") or entry.get("stored_name")
            if dl_name in seen_names:
                seen_names[dl_name] += 1
                stem = Path(dl_name).stem
                ext = Path(dl_name).suffix
                dl_name = f"{stem} ({seen_names[dl_name]}){ext}"
            else:
                seen_names[dl_name] = 0
            zf.write(path, dl_name)

    buf.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"archivos_validados_{timestamp}.zip",
    )


@app.route("/api/stats/ranking", methods=["GET"])
def get_ranking():
    validators = get_validator_stats()
    uploaders = get_uploader_stats()
    return jsonify({"ok": True, "validators": validators, "uploaders": uploaders})


@app.route("/api/stats/records", methods=["GET"])
def records_stats():
    """Retorna estadísticas de registros (filas) de archivos validados."""
    stats = get_record_stats()
    return jsonify({"ok": True, **stats})


@app.route("/api/stats/kpis", methods=["GET"])
def public_kpis():
    """Retorna KPI públicos reconstruidos desde archivos validados."""
    try:
        return jsonify({"ok": True, "kpis": _compute_public_kpis()})
    except Exception as exc:
        logging.exception("Error al calcular KPI públicos")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/stats/recount", methods=["POST"])
def recount_all():
    """Recuenta filas de todos los archivos Excel/CSV que no tengan row_count."""
    from file_store import _connect

    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, stored_name, status, file_type FROM files WHERE row_count IS NULL AND file_type != 'pdf'"
        ).fetchall()

    updated = 0
    for row in rows:
        entry = {"stored_name": row["stored_name"], "status": row["status"]}
        path = get_file_path(entry)
        if path.exists():
            rc = count_file_rows(path)
            if rc is not None:
                update_row_count(row["id"], rc)
                updated += 1

    return jsonify({"ok": True, "updated": updated, "total_checked": len(rows)})


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )
    port = int(os.environ.get("PORT", 5002))
    print(f"\n  KoboUp disponible en http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
