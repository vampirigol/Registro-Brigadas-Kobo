"""Almacén persistente de coordenadas por lugar.

Guarda un diccionario {lugar_normalizado: {lugar, lat, lon, alt, acc, source, updated_at}}
en ``logs/coords_por_lugar.json`` para reutilizar coordenadas en futuras cargas.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config import LOGS_DIR

COORDS_FILE = LOGS_DIR / "coords_por_lugar.json"


def _normalize_lugar(name: str) -> str:
    """Normaliza el nombre del lugar (minúsculas, sin tildes, espacios simples)."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s


def _load() -> Dict[str, Dict[str, Any]]:
    """Carga el archivo de coordenadas. Si falla, retorna dict vacío."""
    try:
        if COORDS_FILE.exists():
            data = json.loads(COORDS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save(data: Dict[str, Dict[str, Any]]) -> None:
    """Guarda el diccionario en disco de forma segura."""
    try:
        COORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = COORDS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(COORDS_FILE)
    except Exception:
        pass


def parse_coords_string(coords: str) -> Tuple[str, str, str, str]:
    """
    Parsea coordenadas en texto y retorna (lat, lon, alt, acc).

    Acepta:
    - "lat lon alt acc"
    - "lat, lon" (coma o punto y coma como separador)
    - cualquier texto que contenga al menos dos números (toma los dos primeros)
    """
    if not coords:
        return "", "", "", ""

    raw = str(coords).strip()
    # Normalizar separadores comunes
    cleaned = raw.replace(";", " ").replace(",", " ")
    parts = [p for p in cleaned.split() if p]
    if len(parts) >= 2:
        lat, lon = parts[0], parts[1]
        alt = parts[2] if len(parts) > 2 else "0"
        acc = parts[3] if len(parts) > 3 else "0"
        return lat, lon, alt, acc

    # Fallback: extraer números en cualquier posición del texto
    nums = re.findall(r"-?\d+(?:\.\d+)?", raw)
    if len(nums) >= 2:
        lat, lon = nums[0], nums[1]
        alt = nums[2] if len(nums) > 2 else "0"
        acc = nums[3] if len(nums) > 3 else "0"
        return lat, lon, alt, acc

    return "", "", "", ""


def coords_to_string(entry: Dict[str, Any]) -> str:
    """Convierte una entrada a string 'lat lon alt acc'."""
    lat = str(entry.get("lat", "")).strip()
    lon = str(entry.get("lon", "")).strip()
    alt = str(entry.get("alt", "0") or "0").strip()
    acc = str(entry.get("acc", "0") or "0").strip()
    if not lat or not lon:
        return ""
    return f"{lat} {lon} {alt} {acc}".strip()


def get_coords_for_lugar(lugar: str) -> Optional[Dict[str, Any]]:
    """Obtiene la entrada de coordenadas para un lugar (normalizado)."""
    key = _normalize_lugar(lugar)
    if not key:
        return None
    data = _load()
    return data.get(key)


def upsert_coords_for_lugar(
    lugar: str,
    lat: str,
    lon: str,
    alt: str | int = "0",
    acc: str | int = "0",
    *,
    source: str = "manual",
) -> Optional[Dict[str, Any]]:
    """
    Guarda/actualiza coordenadas para un lugar.

    - Prioriza entradas de usuario ("manual"/"default") sobre geocodificadas.
    - No sobrescribe una entrada manual existente con una geocodificada.
    """
    lugar = (lugar or "").strip()
    lat = str(lat or "").strip()
    lon = str(lon or "").strip()
    alt = str(alt or "0").strip()
    acc = str(acc or "0").strip()
    if not lugar or not lat or not lon:
        return None

    key = _normalize_lugar(lugar)
    if not key:
        return None

    data = _load()
    existing = data.get(key)
    existing_source = (existing or {}).get("source", "")

    # No pisar manual/default con geocodificado automático
    if existing and source == "geocode" and existing_source in ("manual", "default"):
        return existing

    entry = {
        "lugar": lugar,
        "lat": lat,
        "lon": lon,
        "alt": alt or "0",
        "acc": acc or "0",
        "source": source,
        "updated_at": datetime.now().isoformat(),
    }
    data[key] = entry
    _save(data)
    return entry


def list_coords() -> Dict[str, Dict[str, Any]]:
    """Devuelve todas las coordenadas almacenadas."""
    return _load()
