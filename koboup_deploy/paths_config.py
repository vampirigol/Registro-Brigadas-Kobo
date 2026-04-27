# -*- coding: utf-8 -*-
"""Carpeta prioritaria de validados (históricos) para índice de cohorte; configurable por entorno."""
from __future__ import annotations

import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent

# Por defecto coincide con koboup_deploy/server.py; sobreescribir con env PRIORITY_VALIDATED_DIR
_default = (
    os.environ.get("PRIORITY_VALIDATED_DIR")
    or str(ROOT / "Llenado Kobo tools.bak_20260320" / "archivos_validados_20260411_004650")
)
PRIORITY_VALIDATED_DIR = Path(_default)
