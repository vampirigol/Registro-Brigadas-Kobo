# -*- coding: utf-8 -*-
"""Criterios compartidos: dosis presente, bandas de edad, encabezados, normalización."""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

def column_looks_dx_espir(h: str) -> bool:
    """Celda de texto: diagnóstico a especificar (mg)."""
    n = norm_col(h)
    if n == "dxesp":
        return True
    if "especif" in n and "diagn" in n and "fisioter" not in n and "odo" not in n:
        if "labor" in n:  # diagn resu
            return False
        return True
    return False


def column_looks_tratamiento_o_insumo(h: str) -> bool:
    """Incluye Tratamiento, medicamentos, plan fisio, detalle de entrega, unidades, medicamentos nombres."""
    n = norm_col(h)
    if "especif" in n and "diagn" in n:
        return False
    if n == "tratamiento" or n.startswith("tratamiento "):
        return True
    if n == "tx" or n.startswith("tx "):
        return True
    if "tratamiento indic" in n:
        return True
    if "medicamento" in n and "labor" not in n and "lente" not in n:
        return True
    if "plan de trat" in n or "plan de trat" in h.lower():
        return True
    if "unidades_entre" in n or "unidades entregad" in n:
        return True
    if "se hizo entrega" in n and "tratam" in n:  # categoría, no
        return False
    if "especif" in n and "se entrega" in n and "diagn" not in n:  # detalle de insumo
        return True
    if "categor" in n and "insum" in n:
        return True
    if "insum" in n and "entreg" in n and "diagn" not in n:  # Insumos entregados (categoría)
        return True
    if "nombres espec" in h.lower() or "nombres espe" in n:
        return True
    for hint in ("dosis", "indicad", "recet"):
        if hint in n and "diagn" not in n:
            return True
    return False


def column_looks_service(h: str) -> bool:
    n = norm_col(h)
    if "servicio" in n and "brin" in n:  # asesoría
        return "servicio" in n
    return "servicio que" in n or n == "servicio" or n.startswith("especialidad")


def column_looks_edad(h: str) -> bool:
    n = norm_col(h)
    return n in ("edad", "age", "años", "año")


def column_looks_dx_mg_list(h: str) -> bool:
    """Listado múltiple (checkbox) medicina — opcional en índice."""
    n = norm_col(h)
    if "fisioter" in n or "odo" in n or "o do" in n:  # odon / oft
        return "medicina" in n and "gen" in n
    if "diagn" in n and "medic" in n and "gen" in n:
        return "especif" not in n
    if n in ("diagnosticos", "diagnósticos") and "odon" not in n:
        return True
    return False


def norm_col(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower().replace("ó", "o").replace("í", "i").replace("á", "a")
                  .replace("é", "e").replace("ú", "u").replace("ü", "u").replace("ñ", "n"))


def norm_text(s: str) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    t = "".join(
        c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", t.lower().strip())


def parse_age(age: Optional[object]) -> Optional[int]:
    if age is None:
        return None
    s = str(age).strip()
    if not s or s in ("N/D", "N/A", "—", "-"):
        return None
    m = re.search(r"(\d{1,3})", s)
    if m:
        try:
            a = int(m.group(1))
            return a if 0 <= a < 150 else None
        except ValueError:
            return None
    return None


def age_to_band(age: Optional[int]) -> str:
    if age is None:
        return "desconocida"
    if age < 1:
        return "0-1"
    if age < 2:
        return "1-2"
    if age < 12:
        return "2-11"
    if age < 18:
        return "12-17"
    if age < 65:
        return "18-64"
    return "65+"


# Presente dosis, presentación o pauta explícita (misma heurística base que extract_medicamentos)
_PRES = re.compile(
    r"(\d{1,4}[\s.,]*\s*mg\b|\bmg\b|\bml\b|\bgr\.?\b|tabs?\.?|compr(imi|imidos?)?|"
    r"c[aá]ps?\.?|amp(oll|\.|ol)?|u\.?i\.?|\bui\b|dosis|frasco|jeringa|"
    r"tab\w*\s*\d|\d+\s*tab|\s+x\s*20d|\d+\s*hrs?)",
    re.IGNORECASE,
)


def treatment_text_has_dose_or_presence(text: Optional[str]) -> bool:
    if text is None:
        return False
    t = str(text).strip()
    if len(t) < 2:
        return False
    return bool(_PRES.search(t))


# Alias plan / API
dose_or_presence_ok = treatment_text_has_dose_or_presence


def treatment_incomplete_for_suggestion(text: Optional[str]) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return not treatment_text_has_dose_or_presence(t)
