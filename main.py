#!/usr/bin/env python3
"""
Orquestador principal para la carga masiva de datos desde Excel a KoboToolbox (Enketo).
"""

import json
import logging
import sys
from pathlib import Path

from config import (
    EXCEL_PATH,
    ERROR_LOG_FILE,
    LOGS_DIR,
    RESUME_FROM_ROW,
    STATS_FILE,
    load_mapping,
)
from excel_reader import iterate_excel_rows
from form_filler import FormFiller


def setup_logging() -> None:
    """Configura logging a archivo y consola."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    # Handler para archivo de errores
    file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Logger principal
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def main() -> None:
    """Ejecuta el proceso de carga masiva."""
    setup_logging()
    logger = logging.getLogger(__name__)

    mapping = load_mapping()
    if not mapping:
        logger.error(
            "El archivo mapping.yaml está vacío. Ejecuta discover_form.py para generar "
            "una plantilla y complétala con el mapeo de columnas Excel -> campos del formulario."
        )
        sys.exit(1)

    if not EXCEL_PATH.exists():
        logger.error("No se encontró el archivo Excel: %s", EXCEL_PATH)
        sys.exit(1)

    start_row = RESUME_FROM_ROW if RESUME_FROM_ROW is not None else 0
    if start_row > 0:
        logger.info("Reanudando desde la fila %d", start_row)

    stats = {"total": 0, "exitosos": 0, "fallidos": 0, "errores": [], "tiempo_segundos": 0}

    import time

    start_time = time.perf_counter()
    filler = FormFiller(mapping=mapping)

    try:
        filler.start()
        for row_index, record in iterate_excel_rows(EXCEL_PATH, start_row=start_row):
            stats["total"] += 1
            success = False
            last_error = None
            for attempt in range(3):  # Hasta 3 intentos por registro
                try:
                    success = filler.fill_record(record, row_index)
                    if success:
                        stats["exitosos"] += 1
                        logger.info("Fila %d: enviado correctamente", row_index + 1)
                        break
                except Exception as e:
                    last_error = str(e)
                    logger.error("Fila %d (intento %d): %s", row_index + 1, attempt + 1, e)

            if not success:
                stats["fallidos"] += 1
                stats["errores"].append(
                    {
                        "fila": int(row_index) + 1,
                        "mensaje": last_error or "Envío fallido sin excepción",
                    }
                )

    finally:
        filler.stop()
        stats["tiempo_segundos"] = round(time.perf_counter() - start_time, 2)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    logger.info(
        "Proceso completado. Total: %d, Exitosos: %d, Fallidos: %d, Tiempo: %.2f s",
        stats["total"],
        stats["exitosos"],
        stats["fallidos"],
        stats["tiempo_segundos"],
    )
    logger.info("Estadísticas guardadas en %s", STATS_FILE)


if __name__ == "__main__":
    main()
