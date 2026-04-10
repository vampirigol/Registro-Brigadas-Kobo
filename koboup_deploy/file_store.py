"""
Almacén SQLite para registrar archivos subidos (Excel/PDF) y su estado.
Estados: pendiente → por_validar → validado | reemplazado
También gestiona archivos PDF de referencia organizados por ubicación.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
FILES_DB_PATH = BASE_DIR / "logs" / "files.db"
PENDING_DIR = BASE_DIR / "uploads" / "pendientes"
VALIDATED_DIR = BASE_DIR / "uploads" / "validados"
REFERENCES_DIR = BASE_DIR / "uploads" / "referencias"

VALID_STATUSES = ("pendiente", "por_validar", "validado", "reemplazado")

_SUFFIX_RE = re.compile(
    r"[_\s\-]*(verificar|verificado|validar|validado|completar|completado|"
    r"corregir|corregido|correccion|corrección|revisar|revisado|final)\s*$",
    re.IGNORECASE,
)


def extract_base_name(filename: str) -> str:
    """Extrae el prefijo base removiendo extensión y sufijos de estado."""
    stem = Path(filename).stem
    return _SUFFIX_RE.sub("", stem).rstrip("_- ")


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
