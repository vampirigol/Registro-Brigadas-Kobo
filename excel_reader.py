"""Lectura del archivo Excel fila por fila con conversión segura a string."""

from pathlib import Path

import pandas as pd


def read_excel_rows(
    excel_path: Path,
    sheet_name: int | str = 0,
    start_row: int | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    """
    Lee el archivo Excel y retorna las columnas y las filas como diccionarios.

    Args:
        excel_path: Ruta al archivo .xlsx
        sheet_name: Nombre o índice de la hoja (default: primera hoja)
        start_row: Fila desde la cual empezar (0-indexed). None = desde el inicio.

    Returns:
        Tupla (lista de nombres de columnas, lista de registros como dict).
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype=str, engine="openpyxl")

    # Reemplazar NaN por string vacío
    df = df.fillna("")

    columns = list(df.columns)
    records = []

    for idx, row in df.iterrows():
        if start_row is not None and idx < start_row:
            continue
        record = {}
        for col in columns:
            val = row[col]
            record[str(col)] = _to_safe_string(val)
        records.append(record)

    return columns, records


def iterate_excel_rows(
    excel_path: Path,
    sheet_name: int | str = 0,
    start_row: int | None = None,
):
    """
    Generador que itera fila por fila sobre el Excel (eficiente en memoria).

    Args:
        excel_path: Ruta al archivo .xlsx
        sheet_name: Nombre o índice de la hoja
        start_row: Fila desde la cual empezar (0-indexed)

    Yields:
        Tupla (índice_fila, dict_con_valores_str)
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype=str, engine="openpyxl")
    df = df.fillna("")
    columns = list(df.columns)

    for idx, row in df.iterrows():
        if start_row is not None and idx < start_row:
            continue
        record = {str(col): _to_safe_string(row[col]) for col in columns}
        yield idx, record


def _to_safe_string(value) -> str:
    """Convierte cualquier valor a string de forma segura."""
    if pd.isna(value):
        return ""
    s = str(value).strip()
    return s
