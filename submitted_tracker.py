"""
Rastreo de filas enviadas exitosamente a KoboToolbox.

Guarda un hash (fingerprint) de cada fila enviada con éxito para que,
al recargar el mismo archivo, se identifiquen las filas ya cargadas
y el usuario no las envíe por error nuevamente.

Almacenamiento: logs/filas_enviadas.json
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from config import LOGS_DIR

SUBMITTED_FILE = LOGS_DIR / "filas_enviadas.json"

_KEY_FIELDS = [
    "NAME", "Fecha_de_atenci_n", "Servicio_que_se_brinda",
    "SEX", "AGE", "Diagnostico_Motivo",
]


def compute_row_hash(record: dict) -> str:
    """Calcula un hash MD5 basado en los campos clave de identificación del registro."""
    parts = []
    for f in _KEY_FIELDS:
        val = str(record.get(f, "")).strip().lower()
        parts.append(val)
    fingerprint = "|".join(parts)
    return hashlib.md5(fingerprint.encode("utf-8")).hexdigest()


def _load_store() -> dict:
    """Lee el archivo de filas enviadas."""
    try:
        if SUBMITTED_FILE.exists():
            return json.loads(SUBMITTED_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"submissions": []}


def _save_store(store: dict) -> None:
    """Guarda el archivo de filas enviadas."""
    LOGS_DIR.mkdir(exist_ok=True)
    try:
        SUBMITTED_FILE.write_text(
            json.dumps(store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def mark_row_submitted(record: dict, filename: str = "") -> None:
    """Registra que una fila fue enviada exitosamente."""
    row_hash = compute_row_hash(record)
    store = _load_store()
    existing_hashes = {s["hash"] for s in store["submissions"]}
    if row_hash in existing_hashes:
        return
    store["submissions"].append({
        "hash": row_hash,
        "file": filename,
        "date": datetime.now().isoformat(),
        "name": str(record.get("NAME", ""))[:60],
        "service": str(record.get("Servicio_que_se_brinda", ""))[:40],
    })
    # Mantener máximo las últimas 5000 entradas para evitar archivos enormes
    if len(store["submissions"]) > 5000:
        store["submissions"] = store["submissions"][-5000:]
    _save_store(store)


def get_submitted_hashes() -> set[str]:
    """Retorna el conjunto de hashes de todas las filas enviadas."""
    store = _load_store()
    return {s["hash"] for s in store["submissions"]}


def find_submitted_indices(records: list[dict]) -> list[int]:
    """
    Dado una lista de registros, retorna los índices (0-based) de
    aquellos que ya fueron enviados exitosamente previamente.
    """
    submitted = get_submitted_hashes()
    if not submitted:
        return []
    indices = []
    for i, rec in enumerate(records):
        if compute_row_hash(rec) in submitted:
            indices.append(i)
    return indices
