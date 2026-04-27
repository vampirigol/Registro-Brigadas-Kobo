"""
Almacén SQLite para registrar archivos subidos (Excel/PDF) y su estado.
Estados: pendiente → por_validar → validado | reemplazado
También gestiona archivos PDF de referencia organizados por ubicación.
"""

from __future__ import annotations

import csv
import logging
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
FILES_DB_PATH = BASE_DIR / "logs" / "files.db"
PENDING_DIR = BASE_DIR / "uploads" / "pendientes"
VALIDATED_DIR = BASE_DIR / "uploads" / "validados"
REFERENCES_DIR = BASE_DIR / "uploads" / "referencias"

VALID_STATUSES = ("pendiente", "por_validar", "validado", "reemplazado")
# TTL corto para evitar bloqueos "pegados" si el navegador cierra sin liberar.
EDIT_LOCK_TTL_SECONDS = 3 * 60

_COPY_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")

_STATUS_SUFFIX_RE = re.compile(
    r"[_\s\-]*(verificar|verificado|validar|validado|completar|completado|"
    r"corregir|corregido|correccion|corrección|revisar|revisado|final)"
    r"(\s*\(\d+\))?\s*$",
    re.IGNORECASE,
)

_TIMESTAMP_RE = re.compile(r"[_\s\-]*\d{14}\s*$")


def extract_base_name(filename: str) -> str:
    """Extrae el prefijo base removiendo extensión, (1), sufijos de estado y timestamps."""
    stem = Path(filename).stem
    stem = _STATUS_SUFFIX_RE.sub("", stem)
    stem = _COPY_SUFFIX_RE.sub("", stem)
    stem = _TIMESTAMP_RE.sub("", stem)
    return stem.rstrip("_- ")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(FILES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_files_db() -> None:
    for d in (BASE_DIR / "logs", PENDING_DIR, VALIDATED_DIR, REFERENCES_DIR):
        d.mkdir(exist_ok=True, parents=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                uploaded_by TEXT,
                validated_by TEXT,
                validated_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                size_bytes INTEGER
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)")
        cols = [r[1] for r in conn.execute("PRAGMA table_info(files)").fetchall()]
        if "uploaded_by" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN uploaded_by TEXT")
        if "downloaded_by" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN downloaded_by TEXT")
        if "downloaded_at" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN downloaded_at TEXT")
        if "superseded_by" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN superseded_by INTEGER")
        if "row_count" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN row_count INTEGER")
        if "edit_locked_by" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN edit_locked_by TEXT")
        if "edit_lock_at" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN edit_lock_at TEXT")
        if "edited_validated" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN edited_validated INTEGER DEFAULT 0")
        if "edited_validated_by" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN edited_validated_by TEXT")
        if "edited_validated_at" not in cols:
            conn.execute("ALTER TABLE files ADD COLUMN edited_validated_at TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ref_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                location TEXT NOT NULL,
                uploaded_by TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                size_bytes INTEGER
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_refs_location ON ref_files(location)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kobo_submission_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                file_name TEXT,
                submitted_by TEXT,
                selected_total INTEGER NOT NULL,
                sent_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                submitted_at TEXT NOT NULL,
                details_json TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kobo_logs_submitted_at ON kobo_submission_logs(submitted_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kobo_logs_file_id ON kobo_submission_logs(file_id)"
        )


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    keys = row.keys()
    return {k: row[k] for k in keys}


def add_file_record(
    original_name: str,
    stored_name: str,
    file_type: str,
    status: str = "pendiente",
    size_bytes: Optional[int] = None,
    notes: Optional[str] = None,
    uploaded_by: Optional[str] = None,
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO files (
                original_name, stored_name, file_type, status,
                notes, uploaded_by, created_at, updated_at, size_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (original_name, stored_name, file_type, status, notes, uploaded_by, now, now, size_bytes),
        )
        file_id = cur.lastrowid
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return _row_to_dict(row)


def list_file_records(status: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM files"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_file_record(file_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return _row_to_dict(row) if row else None


def update_status(file_id: int, new_status: str, **kwargs: Any) -> Optional[Dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    sets = ["status = ?", "updated_at = ?"]
    params: list[Any] = [new_status, now]

    if kwargs.get("validated_by"):
        sets.append("validated_by = ?")
        params.append(kwargs["validated_by"])
    if kwargs.get("notes") is not None:
        sets.append("notes = COALESCE(?, notes)")
        params.append(kwargs["notes"])
    if new_status == "validado":
        sets.append("validated_at = ?")
        params.append(now)

    params.append(file_id)
    with _connect() as conn:
        conn.execute(f"UPDATE files SET {', '.join(sets)} WHERE id = ?", params)
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return _row_to_dict(row) if row else None


def mark_file_validated(
    file_id: int, validated_by: Optional[str] = None, notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    return update_status(file_id, "validado", validated_by=validated_by, notes=notes)


def delete_file_record(file_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
    return _row_to_dict(row)


def get_file_path(record: Dict[str, Any]) -> Path:
    base = VALIDATED_DIR if record.get("status") == "validado" else PENDING_DIR
    return base / record["stored_name"]


def ensure_validated_location(record: Dict[str, Any]) -> Path:
    src = get_file_path(record)
    dest = VALIDATED_DIR / record["stored_name"]
    if src.exists() and src != dest:
        dest.parent.mkdir(exist_ok=True, parents=True)
        try:
            shutil.move(str(src), str(dest))
        except Exception:
            pass
    return dest


def supersede_specific_file(file_id: int, replaced_by: int) -> bool:
    """Marca un archivo específico como 'reemplazado' por otro."""
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        row = conn.execute("SELECT id FROM files WHERE id = ?", (file_id,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE files SET status = 'reemplazado', superseded_by = ?, updated_at = ? WHERE id = ?",
            (replaced_by, now, file_id),
        )
    return True


def supersede_matching_files(new_file_id: int, new_original_name: str) -> List[int]:
    """Marca como 'reemplazado' los archivos anteriores con el mismo prefijo base."""
    base = extract_base_name(new_original_name)
    if not base:
        return []

    superseded_ids: List[int] = []
    now = datetime.utcnow().isoformat()

    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, original_name, status FROM files WHERE id != ? AND status != 'reemplazado'",
            (new_file_id,),
        ).fetchall()
        for row in rows:
            if extract_base_name(row["original_name"]) == base:
                conn.execute(
                    "UPDATE files SET status = 'reemplazado', superseded_by = ?, updated_at = ? WHERE id = ?",
                    (new_file_id, now, row["id"]),
                )
                superseded_ids.append(row["id"])
    return superseded_ids


def has_validated_replacement(file_id: int) -> bool:
    """Verifica si existe un archivo validado que reemplace al dado (mismo prefijo)."""
    record = get_file_record(file_id)
    if not record:
        return False
    base = extract_base_name(record["original_name"])
    if not base:
        return False
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id FROM files WHERE id != ? AND status = 'validado'",
            (file_id,),
        ).fetchall()
        for row in rows:
            other = conn.execute("SELECT original_name FROM files WHERE id = ?", (row["id"],)).fetchone()
            if other and extract_base_name(other["original_name"]) == base:
                return True
    return False


# ── Reference files (PDFs de referencia) ──────────────────────────


def add_ref_record(
    original_name: str,
    stored_name: str,
    location: str,
    uploaded_by: Optional[str] = None,
    notes: Optional[str] = None,
    size_bytes: Optional[int] = None,
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO ref_files (original_name, stored_name, location,
                                   uploaded_by, notes, created_at, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (original_name, stored_name, location, uploaded_by, notes, now, size_bytes),
        )
        row = conn.execute("SELECT * FROM ref_files WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_dict(row)


def list_ref_records(location: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = "SELECT * FROM ref_files"
    params: list[Any] = []
    if location:
        sql += " WHERE location = ?"
        params.append(location)
    sql += " ORDER BY location ASC, created_at DESC"
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_ref_record(ref_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM ref_files WHERE id = ?", (ref_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_ref_record(ref_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM ref_files WHERE id = ?", (ref_id,)).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM ref_files WHERE id = ?", (ref_id,))
    return _row_to_dict(row)


def list_ref_locations() -> List[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT location FROM ref_files ORDER BY location ASC"
        ).fetchall()
    return [r[0] for r in rows]


def get_ref_file_path(record: Dict[str, Any]) -> Path:
    return REFERENCES_DIR / record["stored_name"]


# ── Conteo de filas en archivos Excel/CSV ──────────────────────────


def count_file_rows(file_path: Path) -> Optional[int]:
    """Cuenta las filas con datos en un archivo Excel o CSV (excluyendo encabezado)."""
    suffix = file_path.suffix.lower()
    try:
        if suffix in (".xlsx", ".xls"):
            return _count_excel_rows(file_path)
        elif suffix == ".csv":
            return _count_csv_rows(file_path)
    except Exception as exc:
        log.warning("No se pudo contar filas de %s: %s", file_path.name, exc)
    return None


def _count_excel_rows(path: Path) -> int:
    import openpyxl

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    total = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(c is not None for c in row):
                total += 1
    wb.close()
    return total


def _count_csv_rows(path: Path) -> int:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            count = 0
            with open(path, "r", encoding=enc, errors="replace") as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                for row in reader:
                    if any(cell.strip() for cell in row):
                        count += 1
            return count
        except Exception:
            continue
    return 0


def update_row_count(file_id: int, row_count: int) -> None:
    """Actualiza el conteo de filas de un archivo."""
    with _connect() as conn:
        conn.execute(
            "UPDATE files SET row_count = ? WHERE id = ?",
            (row_count, file_id),
        )


def update_file_size_and_row_count(
    file_id: int, size_bytes: int, row_count: int
) -> None:
    """Actualiza tamaño en bytes, filas de datos y marcas updated_at (tras guardar tabla)."""
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE files SET size_bytes = ?, row_count = ?, updated_at = ? WHERE id = ?",
            (size_bytes, row_count, now, file_id),
        )


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _is_lock_expired(lock_at: Optional[str]) -> bool:
    dt = _parse_iso(lock_at)
    if not dt:
        return True
    return (datetime.utcnow() - dt).total_seconds() > EDIT_LOCK_TTL_SECONDS


def get_edit_lock(file_id: int) -> Optional[Dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, edit_locked_by, edit_lock_at FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
    if not row:
        return None
    locked_by = row["edit_locked_by"]
    lock_at = row["edit_lock_at"]
    if not locked_by or _is_lock_expired(lock_at):
        return None
    return {"locked_by": locked_by, "locked_at": lock_at}


def acquire_edit_lock(file_id: int, editor_name: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    editor = str(editor_name or "").strip()
    if not editor:
        return False, {"error": "editor_name vacío"}
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, edit_locked_by, edit_lock_at FROM files WHERE id = ?",
            (file_id,),
        ).fetchone()
        if not row:
            return False, None
        current_by = (row["edit_locked_by"] or "").strip()
        current_at = row["edit_lock_at"]
        if current_by and current_by != editor and not _is_lock_expired(current_at):
            return False, {"locked_by": current_by, "locked_at": current_at}
        conn.execute(
            "UPDATE files SET edit_locked_by = ?, edit_lock_at = ?, updated_at = ? WHERE id = ?",
            (editor, now, now, file_id),
        )
    return True, {"locked_by": editor, "locked_at": now}


def refresh_edit_lock(file_id: int, editor_name: str) -> tuple[bool, Optional[Dict[str, Any]]]:
    return acquire_edit_lock(file_id, editor_name)


def release_edit_lock(file_id: int, editor_name: Optional[str] = None, force: bool = False) -> bool:
    editor = str(editor_name or "").strip()
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        if force:
            cur = conn.execute(
                "UPDATE files SET edit_locked_by = NULL, edit_lock_at = NULL, updated_at = ? WHERE id = ?",
                (now, file_id),
            )
            return cur.rowcount > 0
        if not editor:
            return False
        cur = conn.execute(
            """
            UPDATE files
            SET edit_locked_by = NULL, edit_lock_at = NULL, updated_at = ?
            WHERE id = ? AND edit_locked_by = ?
            """,
            (now, file_id, editor),
        )
        return cur.rowcount > 0


def get_record_stats() -> Dict[str, Any]:
    """Retorna estadísticas de registros (filas) por estado de archivo."""
    with _connect() as conn:
        total_rows = conn.execute(
            "SELECT COALESCE(SUM(row_count), 0) FROM files WHERE status != 'reemplazado' AND row_count IS NOT NULL"
        ).fetchone()[0]
        validated_rows = conn.execute(
            "SELECT COALESCE(SUM(row_count), 0) FROM files WHERE status = 'validado' AND row_count IS NOT NULL"
        ).fetchone()[0]
        pending_rows = conn.execute(
            "SELECT COALESCE(SUM(row_count), 0) FROM files WHERE status = 'pendiente' AND row_count IS NOT NULL"
        ).fetchone()[0]
        review_rows = conn.execute(
            "SELECT COALESCE(SUM(row_count), 0) FROM files WHERE status = 'por_validar' AND row_count IS NOT NULL"
        ).fetchone()[0]
        validated_files = conn.execute(
            "SELECT COUNT(*) FROM files WHERE status = 'validado'"
        ).fetchone()[0]
        total_files = conn.execute(
            "SELECT COUNT(*) FROM files WHERE status != 'reemplazado'"
        ).fetchone()[0]
    return {
        "total_records": total_rows,
        "validated_records": validated_rows,
        "pending_records": pending_rows,
        "review_records": review_rows,
        "validated_files": validated_files,
        "total_files": total_files,
    }


# ── Estadísticas de validación ─────────────────────────────────────


def get_validator_stats() -> List[Dict[str, Any]]:
    """Retorna ranking de personas por cantidad de archivos validados."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT validated_by AS name, COUNT(*) AS count,
                   MAX(validated_at) AS last_validated_at
            FROM files
            WHERE validated_by IS NOT NULL AND validated_by != ''
            GROUP BY validated_by
            ORDER BY count DESC, last_validated_at DESC
            """
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_uploader_stats() -> List[Dict[str, Any]]:
    """Retorna ranking de personas por cantidad de archivos subidos."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT uploaded_by AS name, COUNT(*) AS count,
                   MAX(created_at) AS last_upload_at
            FROM files
            WHERE uploaded_by IS NOT NULL AND uploaded_by != ''
            GROUP BY uploaded_by
            ORDER BY count DESC, last_upload_at DESC
            """
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def log_kobo_submission(
    *,
    file_id: Optional[int],
    file_name: Optional[str],
    submitted_by: Optional[str],
    selected_total: int,
    sent_count: int,
    failed_count: int,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    details_json = None
    if details:
        try:
            import json

            details_json = json.dumps(details, ensure_ascii=False)
        except Exception:
            details_json = None
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO kobo_submission_logs (
                file_id, file_name, submitted_by, selected_total,
                sent_count, failed_count, submitted_at, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                file_name,
                submitted_by,
                int(selected_total),
                int(sent_count),
                int(failed_count),
                now,
                details_json,
            ),
        )
        row = conn.execute(
            "SELECT * FROM kobo_submission_logs WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return _row_to_dict(row) if row else {}


def list_kobo_submission_logs(limit: int = 100) -> List[Dict[str, Any]]:
    n = max(1, min(int(limit or 100), 500))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, file_id, file_name, submitted_by, selected_total,
                   sent_count, failed_count, submitted_at, details_json
            FROM kobo_submission_logs
            ORDER BY submitted_at DESC
            LIMIT ?
            """,
            (n,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]
