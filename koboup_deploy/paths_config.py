# -*- coding: utf-8 -*-
"""Carpeta prioritaria de validados (históricos) para índice de cohorte; configurable por entorno."""
from __future__ import annotations

import os
from pathlib import Path

BASE = Path(__file__).resolve().parent

# Históricos Excel/CSV *extra* para el índice (además de "validado" en BD vía file_store).
# En producción, rutas fuera de /opt/koboup (p. ej. otra copia de proyecto) suelen no existir.
# Opcional: variable de entorno PRIORITY_VALIDATED_DIR
_default = os.environ.get("PRIORITY_VALIDATED_DIR")
if not _default:
    _default = str(BASE / "data" / "priority_validated")
PRIORITY_VALIDATED_DIR = Path(_default)
