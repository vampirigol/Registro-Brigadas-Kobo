"""
Wrapper sobre pdf_extractor para la interfaz que server.py espera.
Exporta: extract_pdf_records(pdf_path, backend) y OUT_XLSX.
"""

from pathlib import Path

import pandas as pd

from config import PROJECT_ROOT
from pdf_extractor import extract_and_to_records

OUT_XLSX = PROJECT_ROOT / "outputs" / "pdf_extract.xlsx"


def extract_pdf_records(pdf_path: Path, backend: str = "tesseract") -> dict:
    """
    Extrae registros del PDF y genera un Excel de salida.

    Args:
        pdf_path: Ruta al archivo PDF.
        backend: "tesseract" para forzar OCR, "pdfplumber" para texto nativo.

    Returns:
        Dict con "records" (lista de dicts) y metadata.
    """
    force_ocr = backend == "tesseract"
    records, parsed_info = extract_and_to_records(pdf_path, force_ocr=force_ocr)

    OUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    if records:
        df = pd.DataFrame(records)
        df.to_excel(OUT_XLSX, index=False, engine="openpyxl")

    return {
        "records": records,
        "count": len(records),
        "backend": backend,
        "info": parsed_info,
    }
