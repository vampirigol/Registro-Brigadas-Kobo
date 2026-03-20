#!/usr/bin/env python3
"""
Crea 'excel_de_prueba.xlsx' con columnas basadas en el formulario Brigadas de salud
y 1 fila de datos de paciente para validar el llenado automático.
"""
from pathlib import Path

import pandas as pd

# Directorio del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent

# Columnas del Excel ( nombres que excel_loader mapea a campos internos )
# Usamos los nombres que EXCEL_TO_INTERNAL reconoce
COLUMNAS = [
    "Fecha de Atención",
    "Nombre del Paciente",
    "Sexo",
    "Edad",
    "Fecha de nacimiento",
    "Estado brigada",
    "Lugar",
    "Modalidad",
    "Primera vez o seguimiento",
    "Servicio que se brinda",
    "Padecimiento",
    "Talla (cm)",
    "Peso (kg)",
    "¿Entrega Tratamiento?",
    "Insumos Entregados",
    "¿Ref?",
    "¿A dónde?",
    "Motivo Ref.",
    "Estatus",
    "Acompañante",
    "Consentimiento",
]

# 1 fila de datos de prueba (valores que coinciden con opciones del formulario)
FILA_PRUEBA = {
    "Fecha de Atención": "2026-03-11",
    "Nombre del Paciente": "SANDRA MURILLO ESPINOZA",
    "Sexo": "F",
    "Edad": "31",
    "Fecha de nacimiento": "1995-01-15",
    "Estado brigada": "Baja California Sur",
    "Lugar": "Santa Rosalía",
    "Modalidad": "Móvil",
    "Primera vez o seguimiento": "Primera vez",
    "Servicio que se brinda": "Oftalmología",
    "Padecimiento": "Control clínico",
    "Talla (cm)": "154",
    "Peso (kg)": "74",
    "¿Entrega Tratamiento?": "Si",
    "Insumos Entregados": "Lentes, medicamento",
    "¿Ref?": "No",
    "¿A dónde?": "",
    "Motivo Ref.": "",
    "Estatus": "Ciudadano Mexicano",
    "Acompañante": "",
    "Consentimiento": "Si",
}


def main():
    out_path = PROJECT_ROOT / "excel_de_prueba.xlsx"
    df = pd.DataFrame([FILA_PRUEBA], columns=COLUMNAS)
    df.to_excel(out_path, index=False, engine="openpyxl")
    print(f"✅ Creado: {out_path}")
    print("Columnas:", list(df.columns))
    print("Fila de datos:", dict(FILA_PRUEBA))
    print("\nPara probar: sube este Excel en la app y pulsa 'Iniciar carga'.")


if __name__ == "__main__":
    main()
