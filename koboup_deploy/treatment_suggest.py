# -*- coding: utf-8 -*-
"""
Sugerencias: pauta JSON (dosis_referencia) + frecuencias de cohorte (índice generado).
"""
from __future__ import annotations

import difflib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from treatment_criteria import (
    age_to_band,
    norm_text,
    parse_age,
    treatment_incomplete_for_suggestion,
    treatment_text_has_dose_or_presence,
)

BASE = Path(__file__).resolve().parent
DATA = Path(BASE) / "data"
DOSIS_PATH = DATA / "dosis_referencia.json"
COHORT_PATH = DATA / "cohort_treatment_index.json"

_lock = threading.RLock()
_dosis_cache: dict[str, Any] = {}
_cohort_cache: dict[str, Any] = {}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def load_dosis_referencia() -> dict[str, Any]:
    with _lock:
        global _dosis_cache
        t = (DOSIS_PATH).stat().st_mtime if DOSIS_PATH.exists() else 0.0
        if _dosis_cache.get("_mtime") != t:
            _dosis_cache = _load_json(DOSIS_PATH)
            _dosis_cache["_mtime"] = t
        return {k: v for k, v in _dosis_cache.items() if k != "_mtime"}


def load_cohort_index() -> dict[str, Any]:
    with _lock:
        global _cohort_cache
        t = (COHORT_PATH).stat().st_mtime if COHORT_PATH.exists() else 0.0
        if _cohort_cache.get("_mtime") != t:
            _cohort_cache = _load_json(COHORT_PATH)
            _cohort_cache["_mtime"] = t
        return {k: v for k, v in _cohort_cache.items() if k != "_mtime"}


def pauta_suggestions(trat_text: str, band: str) -> list[dict[str, Any]]:
    pauta = load_dosis_referencia()
    drogas = pauta.get("drogas") or pauta.get("drugs") or {}
    nt = norm_text(trat_text)
    out: list[dict[str, Any]] = []
    for drug, bands in drogas.items():
        if not isinstance(bands, dict) or not drug or drug in ("version", "nota_legal"):
            continue
        dk = drug.replace(" ", "_")
        if not re.search(rf"\b{re.escape(drug)}\b", nt, re.I) and not re.search(
            rf"\b{re.escape(dk)}\b", nt, re.I
        ):
            continue
        binfo = bands.get(band) or bands.get("18-64") or next(iter(bands.values()), None)
        if not isinstance(binfo, dict):
            continue
        tx = (binfo.get("texto") or binfo.get("text") or "").strip()
        if not tx:
            continue
        out.append(
            {
                "texto": tx,
                "fuente": "pauta",
                "drogas": drug,
                "banda": band,
                "n": 0,
            }
        )
    return out


def _cohort_suggestions(
    dx_esp: str, serv: str, band: str, limit: int = 8
) -> list[dict[str, Any]]:
    cdata = load_cohort_index()
    ent = cdata.get("entries") or []
    if not ent:
        return []
    dxk = norm_text(dx_esp)[:200]
    sk = norm_text(serv)[:60]
    scored: list[tuple[float, dict[str, Any]]] = []
    for e in ent:
        eb = e.get("edad_banda", "")
        if band not in ("desconocida", "") and eb not in (band, "desconocida", ""):
            if band != eb:
                continue
        s_dx = 0.25
        s_sv = 0.15
        e_dx = (e.get("dxk") or "")
        e_sv = (e.get("servk") or "")
        if len(dxk) > 1:
            s_dx = difflib.SequenceMatcher(None, dxk, e_dx).ratio()
        if len(sk) > 1 and len(e_sv) > 1:
            s_sv = difflib.SequenceMatcher(None, sk, e_sv).ratio()
        if len(dxk) > 2 and s_dx < 0.1 and s_sv < 0.12:
            continue
        w = 0.65 * s_dx + 0.2 * s_sv
        c = int(e.get("c") or 0)
        score = w * 1.0 + (min(c, 200) / 2000.0)  # favor frequent a bit
        tx = (e.get("texto") or "").strip()
        if not treatment_text_has_dose_or_presence(tx):
            continue
        scored.append(
            (score, {"texto": tx, "fuente": "cohorte", "n": c, "banda": e.get("edad_banda", "")})
        )
    scored.sort(key=lambda t: t[0], reverse=True)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, s in scored:
        k = s["texto"][:200]
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def suggest_treatment(
    body: dict[str, Any] | None,
) -> dict[str, Any]:
    b = body or {}
    t_raw = str(b.get("tratamiento_actual") or b.get("tratamiento") or b.get("Tratamiento") or "")
    t_raw = t_raw.strip()
    edad = parse_age(b.get("edad"))
    band = age_to_band(edad) if edad is not None else b.get("edad_banda") or "desconocida"
    if isinstance(band, str) and not band:
        band = "desconocida"
    serv = b.get("servicio") or b.get("Servicio_que_se_brinda") or ""
    dx_esp = (
        b.get("dx_espir")
        or b.get("Especificar diagnóstico (Medicina General)")
        or b.get("especificar_diagnostico")
        or ""
    )
    if isinstance(dx_esp, (list, dict)):
        dx_esp = " ".join(str(x) for x in dx_esp) if isinstance(dx_esp, list) else str(dx_esp)
    else:
        dx_esp = str(dx_esp or "")

    incomplete = treatment_incomplete_for_suggestion(t_raw)

    seen_txt: set[str] = set()
    sugg: list[dict[str, Any]] = []
    for p in pauta_suggestions(t_raw, str(band)):
        k0 = p["texto"][:100] if p.get("texto") else ""
        if k0 in seen_txt:
            continue
        seen_txt.add(k0)
        p.pop("banda", None)
        sugg.append(p)
    for c in _cohort_suggestions(dx_esp, str(serv or ""), str(band), limit=10):
        k1 = c["texto"][:100] if c.get("texto") else ""
        if not k1 or k1 in seen_txt:
            continue
        seen_txt.add(k1)
        c.pop("banda", None)
        sugg.append(c)
    pauta = load_dosis_referencia()
    cidx = load_cohort_index()
    g_at = cidx.get("generated_at", "")
    return {
        "ok": True,
        "incompleto": incomplete,
        "edad_parsed": edad,
        "edad_banda": str(band),
        "pauta_version": pauta.get("version"),
        "cohorte_fila_index": cidx.get("fila_tto_con_dosis"),
        "cohorte_archivo_index": cidx.get("file_count"),
        "cohorte_generado": g_at,
        "suggestions": sugg[:20],
    }


def cohort_stats() -> dict[str, Any]:
    c = load_cohort_index()
    p = load_dosis_referencia()
    d_path = str(DOSIS_PATH)
    c_path = str(COHORT_PATH)
    return {
        "ok": True,
        "dosis_referencia_path": d_path,
        "dosis_referencia_exists": DOSIS_PATH.exists(),
        "dosis_referencia_version": p.get("version"),
        "cohort_index_path": c_path,
        "cohort_index_exists": COHORT_PATH.exists(),
        "cohort_generated_at": c.get("generated_at"),
        "cohort_file_count": c.get("file_count"),
        "cohort_treatment_rows": c.get("fila_tto_con_dosis"),
        "cohort_entry_count": len(c.get("entries") or []),
    }
