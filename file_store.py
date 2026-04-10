"""
Pequeño almacén SQLite para registrar archivos subidos (Excel/PDF) y su estado.
Permite listar, marcar como validados y resolver rutas físicas en disco.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import LOGS_DIR, PROJECT_ROOT

# Rutas base
FILES_DB_PATH = LOGS_DIR / "files.db"
FILES_DIR = PROJECT_ROOT / "uploads"
PENDING_DIR = FILES_DIR / "pendientes"
VALIDATED_DIR = FILES_DIR / "validados"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(FILES_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_files_db() -> None:
    """Crea carpetas y tabla SQLite si no existen."""
    for d in (LOGS_DIR, FILES_DIR, PENDING_DIR, VALIDATED_DIR):
        d.mkdir(exist_ok=True)
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
                validated_by TEXT,
                validated_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                size_bytes INTEGER
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)")


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "original_name": row["original_name"],
        "stored_name": row["stored_name"],
        "file_type": row["file_type"],
        "status": row["status"],
        "notes": row["notes"],
        "validated_by": row["validated_by"],
        "validated_at": row["validated_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "size_bytes": row["size_bytes"],
    }


def add_file_record(
    original_name: str,
    stored_name: str,
    file_type: str,
    status: str = "pendiente",
    size_bytes: Optional[int] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Inserta un registro y devuelve el diccionario con sus campos."""
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO files (
                original_name, stored_name, file_type, status,
                notes, created_at, updated_at, size_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                original_name,
                stored_name,
                file_type,
                status,
                notes,
                now,
                now,
                size_bytes,
            ),
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


def update_notes(file_id: int, notes: Optional[str]) -> Optional[Dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            "UPDATE files SET notes = ?, updated_at = ? WHERE id = ?",
            (notes, now, file_id),
        )
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return _row_to_dict(row) if row else None


def mark_file_validated(
    file_id: int, validated_by: Optional[str] = None, notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE files
            SET status = 'validado',
                validated_at = ?,
                validated_by = ?,
                notes = COALESCE(?, notes),
                updated_at = ?
            WHERE id = ?
            """,
            (now, validated_by, notes, now, file_id),
        )
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return _row_to_dict(row) if row else None


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
    """
    Mueve el archivo físico a la carpeta de validados (si está en pendientes)
    y devuelve la ruta final.
    """
    src = get_file_path(record)
    dest = VALIDATED_DIR / record["stored_name"]
    if src.exists() and src != dest:
        dest.parent.mkdir(exist_ok=True, parents=True)
        try:
            shutil.move(str(src), str(dest))
        except Exception:
            pass
    return dest

