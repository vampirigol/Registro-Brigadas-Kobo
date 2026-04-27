#!/usr/bin/env python3
"""Regenera koboup_deploy/data/cohort_treatment_index.json (archivos validados + carpeta prioritaria)."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent / "koboup_deploy"
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from cohort_index_builder import build_and_write  # noqa: E402

if __name__ == "__main__":
    d = build_and_write()
    print("OK", d.get("file_count"), "archivos,", d.get("fila_tto_con_dosis"), "filas con tratamiento y dosis")
