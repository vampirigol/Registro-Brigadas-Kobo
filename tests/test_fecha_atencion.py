#!/usr/bin/env python3
"""
Tests para la normalización y llenado de Fecha de atención.
Ejecutar: python -m pytest tests/test_fecha_atencion.py -v
O: python tests/test_fecha_atencion.py
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_norm_fecha():
    """Verifica que _norm_fecha convierta varios formatos a YYYY-MM-DD."""
    from filling_rules import _norm_fecha

    # YYYY-MM-DD (Excel/Pandas típico)
    assert _norm_fecha("2026-03-11") == "2026-03-11"
    assert _norm_fecha("2026-3-5") == "2026-03-05"

    # YYYY-MM-DD HH:MM:SS (Excel exporta datetime así)
    assert _norm_fecha("2026-03-11 00:00:00") == "2026-03-11"
    assert _norm_fecha("2026-02-17 12:30:45") == "2026-02-17"

    # DD/MM/YYYY
    assert _norm_fecha("17/02/2026") == "2026-02-17"
    assert _norm_fecha("11/03/2026") == "2026-03-11"
    assert _norm_fecha("1/1/26") == "2026-01-01"

    # DD-MM-YYYY
    assert _norm_fecha("17-02-2026") == "2026-02-17"

    # Excel serial (número de días desde 1899-12-30)
    result = _norm_fecha("45379")
    assert re.match(r"\d{4}-\d{2}-\d{2}", result), f"Esperado YYYY-MM-DD, obtuvo {result}"

    # Vacío
    assert _norm_fecha("") == ""
    assert _norm_fecha(None) == ""


def test_apply_rules_fecha():
    """Verifica que apply_rules produzca Fecha_de_atenci_n en YYYY-MM-DD."""
    from filling_rules import apply_rules
    from datetime import date

    # Record con fecha en formato Excel
    record = {
        "Fecha_de_atenci_n": "2026-03-11 00:00:00",
        "NAME": "Test",
        "SEX": "F",
        "Servicio_que_se_brinda": "Medicina General",
    }
    out = apply_rules(record)
    assert "Fecha_de_atenci_n" in out
    assert out["Fecha_de_atenci_n"] == "2026-03-11"

    # Record con fecha DD/MM/YYYY
    record2 = {"Fecha_de_atenci_n": "17/02/2026", "NAME": "X", "SEX": "M"}
    out2 = apply_rules(record2)
    assert out2["Fecha_de_atenci_n"] == "2026-02-17"

    # Record sin fecha → usa hoy
    record3 = {"NAME": "Y", "SEX": "F"}
    out3 = apply_rules(record3)
    assert "Fecha_de_atenci_n" in out3
    assert out3["Fecha_de_atenci_n"] == date.today().isoformat()


def test_create_excel_and_normalize():
    """Crea Excel de prueba y verifica que la fecha se normalice correctamente."""
    from excel_loader import load_excel_to_records, EXCEL_TO_INTERNAL
    from filling_rules import apply_rules

    excel_path = PROJECT_ROOT / "excel_de_prueba.xlsx"
    if not excel_path.exists():
        # Crear si no existe
        from create_excel_prueba import main as create_main
        create_main()

    if excel_path.exists():
        records = load_excel_to_records(excel_path)
        assert records, "Excel vacío"
        rec = records[0]
        # Aplicar reglas
        out = apply_rules(rec)
        assert "Fecha_de_atenci_n" in out
        fecha = out["Fecha_de_atenci_n"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", fecha), f"Fecha debe ser YYYY-MM-DD: {fecha}"

if __name__ == "__main__":
    print("Ejecutando tests de Fecha de atención...")
    test_norm_fecha()
    print("  ✓ test_norm_fecha")
    test_apply_rules_fecha()
    print("  ✓ test_apply_rules_fecha")
    test_create_excel_and_normalize()
    print("  ✓ test_create_excel_and_normalize")
    print()
    print("Todos los tests pasaron.")
