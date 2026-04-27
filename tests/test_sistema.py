"""
Tests de funcionamiento del sistema de carga KoboToolbox.
Ejecutar desde la raíz del proyecto: ./venv/bin/python tests/test_sistema.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Añadir raíz del proyecto al path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pandas as pd


def ok(name):
    print(f"  OK  {name}")


def fail(name, e):
    print(f"  FAIL {name}: {e}")
    return 1


def run_tests():
    nfail = 0

    # --- Excel loader ---
    print("\n--- excel_loader ---")
    try:
        from excel_loader import _normalize_fecha
        assert _normalize_fecha("2026-02-17") == "2026-02-17"
        assert _normalize_fecha("17/02/2026") == "2026-02-17"
        ok("_normalize_fecha")
    except Exception as e:
        nfail += fail("_normalize_fecha", e)

    try:
        from excel_loader import _normalize_sex
        assert _normalize_sex("F") == "F"
        assert _normalize_sex("M") == "H"
        ok("_normalize_sex")
    except Exception as e:
        nfail += fail("_normalize_sex", e)

    try:
        from excel_loader import _normalize_si_no
        assert _normalize_si_no("Sí") == "1"
        assert _normalize_si_no("No") == "0"
        ok("_normalize_si_no")
    except Exception as e:
        nfail += fail("_normalize_si_no", e)

    try:
        from excel_loader import load_excel_to_records, validate_records
        df = pd.DataFrame([{
            "Fecha de Atención": "2026-02-17",
            "Lugar": "Escuela Test",
            "Nombre del Paciente": "Juan Pérez",
            "Servicio": "Odontología",
            "Padecimiento": "Limpieza",
            "Talla (cm)": "170",
            "Peso (kg)": "70",
            "¿Entrega?": "Sí",
            "Insumos": "Kit dental",
            "¿Ref?": "No",
            "Edad": "30",
            "Sexo": "H",
            "Modalidad": "Móvil",
            "Estado": "BCS",
            "Consent.": "SÍ",
            "Estatus": "Ciudadano Mex",
            "Minoría": "No",
        }])
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            df.to_excel(f.name, index=False, engine="openpyxl")
            try:
                recs = load_excel_to_records(Path(f.name))
                assert len(recs) == 1
                r = recs[0]
                assert r["NAME"] == "Juan Pérez"
                assert r["Estado_brigada"] == "BCS"
                v = validate_records(recs)
                assert v["valid"] == 1
                ok("load_excel_to_records + validate_records")
            finally:
                Path(f.name).unlink(missing_ok=True)
    except Exception as e:
        nfail += fail("load_excel + validate", e)

    try:
        from excel_loader import load_excel_to_records
        from filling_rules import apply_rules

        df = pd.DataFrame([{
            "Fecha de Atención": "2026-02-17",
            "Lugar": "Escuela Test",
            "Nombre del Paciente": "Juana Pérez",
            "Servicio": "Odontología",
            "Padecimiento": "Valoración",
            "Edad": "31",
            "Sexo": "F",
            "Estado": "BCS",
            "Especificar Minoría Étnica": "Maya",
        }])
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            df.to_excel(f.name, index=False, engine="openpyxl")
            try:
                recs = load_excel_to_records(Path(f.name))
                assert len(recs) == 1
                r = recs[0]
                assert r["Especificar_Minor_a_tnica"] == "Maya"
                out = apply_rules(r)
                assert out["_Pertenece_a_alguna_minor_a_t"] == "1"
                assert out["Especificar_Minor_a_tnica"] == "Maya"
                ok("minoría étnica especificada activa Sí")
            finally:
                Path(f.name).unlink(missing_ok=True)
    except Exception as e:
        nfail += fail("minoría étnica especificada", e)

    # --- filling_rules ---
    print("\n--- filling_rules ---")
    try:
        from filling_rules import apply_rules
        rec = {
            "NAME": "María López",
            "Fecha_de_atenci_n": "2026-02-17",
            "SEX": "F",
            "AGE": "25",
            "Estado_brigada": "BCS",
            "Lugar": "Ligui",
            "Servicio_que_se_brinda": "Laboratorio",
            "Diagnostico_Motivo": "Control",
            "HEI": "160",
            "WEI": "55",
            "Resultados_Lab_Insumos": "Glucosa",
            "Referencia": "No",
        }
        out = apply_rules(rec)
        assert out["NAME"] == "María López"
        assert out["CONS1"] == "1"
        assert out["POC"] == "BCS"
        assert out["Servicio_que_se_brinda"] == "Laboratorios"
        assert out["REF"] == "0"
        ok("apply_rules")
    except Exception as e:
        nfail += fail("apply_rules", e)

    try:
        from filling_rules import apply_rules
        rec = {"NAME": "Niño", "AGE": "10", "SEX": "H", "Estado_brigada": "BCS", "Lugar": "X"}
        out = apply_rules(rec)
        assert out.get("CGR") == "Cuidadora mujer"
        ok("apply_rules CGR menor")
    except Exception as e:
        nfail += fail("apply_rules CGR", e)

    # --- runner ---
    print("\n--- runner ---")
    try:
        from runner import _normalize_record
        row = {
            "Nombre del Paciente": "Ana",
            "Fecha de Atención": "2026-02-17",
            "Estado": "BCS",
        }
        out = _normalize_record(row, {"NAME", "Fecha_de_atenci_n", "Estado_brigada"})
        assert out.get("NAME") == "Ana"
        assert out.get("Estado_brigada") == "BCS"
        ok("_normalize_record")
    except Exception as e:
        nfail += fail("_normalize_record", e)

    # --- config ---
    print("\n--- config ---")
    try:
        from config import load_mapping
        m = load_mapping()
        assert "NAME" in m and "POC" in m
        ok("load_mapping")
    except Exception as e:
        nfail += fail("load_mapping", e)

    # --- API Flask ---
    print("\n--- API ---")
    try:
        from server import app
        app.config["TESTING"] = True
        client = app.test_client()

        r = client.get("/api/config")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "form_url" in data
        ok("GET /api/config")

        r = client.get("/api/status")
        assert r.status_code == 200
        assert b"status" in r.data
        ok("GET /api/status")

        r = client.post("/api/load-excel")
        assert r.status_code == 400
        ok("POST /api/load-excel sin archivo → 400")

        r = client.post("/api/start", data=json.dumps({}), content_type="application/json")
        assert r.status_code == 400
        ok("POST /api/start sin archivo → 400")

        r = client.post(
            "/api/confirm-row",
            data=json.dumps({"action": "invalid"}),
            content_type="application/json",
        )
        assert r.status_code == 400
        ok("POST /api/confirm-row invalid → 400")

        r = client.get("/")
        assert r.status_code == 200
        assert b"Carga masiva" in r.data or b"KoboToolbox" in r.data
        ok("GET / (HTML)")
    except Exception as e:
        nfail += fail("API", e)

    return nfail


if __name__ == "__main__":
    print("Testing sistema de carga KoboToolbox")
    nfail = run_tests()
    print("\n" + "=" * 50)
    if nfail == 0:
        print("Todos los tests pasaron.")
        sys.exit(0)
    else:
        print(f"Fallaron {nfail} test(s).")
        sys.exit(1)
