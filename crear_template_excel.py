#!/usr/bin/env python3
"""
Crea Plantilla_Carga_KoboToolbox.xlsx: template efectivo para llenar datos
y subirlos a la aplicación. Usa exactamente los nombres de columna que
excel_loader reconoce (EXCEL_TO_INTERNAL).
"""
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent

# Columnas en orden lógico para captura. Nombres que excel_loader mapea correctamente.
COLUMNAS = [
    "Fecha de Atención",
    "Nombre del Paciente",
    "Sexo",
    "Edad",
    "Fecha de nacimiento",
    "Estado",
    "Lugar",
    "Modalidad",
    "Primera vez o seguimiento",
    "Servicio que se brinda",
    "Padecimiento",
    "Talla (cm)",
    "Peso (kg)",
    "¿Entrega Tratamiento?",
    "Insumos Entregados",
    "¿Se hizo referencia?",
    "¿A dónde?",
    "Motivo Ref.",
    "Estatus",
    "Acompañante",
]

# Valores válidos del formulario (usar exactamente estos para que funcione)
VALORES_ESTADO = ["Baja California Sur", "Baja Californa Sur", "Chihuahua", "Sonora", "Baja California", "Nuevo León", "Otro"]
VALORES_MODALIDAD = ["Móvil", "Albergues", "Centros Comunitarios", "Clínica Adventista", "Escuelas"]
VALORES_SERVICIO = ["Medicina General", "Dental", "Fisioterapia", "Oftalmología", "Laboratorios"]
VALORES_FOLLOWUP = ["Primera vez", "Seguimiento", "Atención Única"]
VALORES_ESTATUS = ["Ciudadano Mexicano", "En tránsito", "Retornado", "Solicitante de asilo", "Refugiado", "Residente temporal", "Residente permanente", "Prefiero no responder"]
VALORES_SI_NO = ["Si", "No", "Sí"]
VALORES_SEXO = ["F", "M", "Femenino", "Masculino"]

# Fila de ejemplo completa
EJEMPLO_COMPLETO = {
    "Fecha de Atención": "2026-03-11",
    "Nombre del Paciente": "JUAN PÉREZ LÓPEZ",
    "Sexo": "M",
    "Edad": "35",
    "Fecha de nacimiento": "1991-02-20",
    "Estado": "Baja California Sur",
    "Lugar": "Santa Rosalía",
    "Modalidad": "Móvil",
    "Primera vez o seguimiento": "Primera vez",
    "Servicio que se brinda": "Medicina General",
    "Padecimiento": "Control de presión arterial",
    "Talla (cm)": "170",
    "Peso (kg)": "75",
    "¿Entrega Tratamiento?": "Si",
    "Insumos Entregados": "Medicamento antihipertensivo",
    "¿Se hizo referencia?": "No",
    "¿A dónde?": "",
    "Motivo Ref.": "",
    "Estatus": "Ciudadano Mexicano",
    "Acompañante": "",
}

# Fila de ejemplo mínima (solo obligatorios)
EJEMPLO_MINIMO = {
    "Fecha de Atención": "2026-03-12",
    "Nombre del Paciente": "MARÍA GARCÍA",
    "Sexo": "F",
    "Edad": "28",
    "Fecha de nacimiento": "",
    "Estado": "Chihuahua",
    "Lugar": "Juárez",
    "Modalidad": "Móvil",
    "Primera vez o seguimiento": "Primera vez",
    "Servicio que se brinda": "Dental",
    "Padecimiento": "Revisión dental",
    "Talla (cm)": "165",
    "Peso (kg)": "62",
    "¿Entrega Tratamiento?": "No",
    "Insumos Entregados": "",
    "¿Se hizo referencia?": "No",
    "¿A dónde?": "",
    "Motivo Ref.": "",
    "Estatus": "Ciudadano Mexicano",
    "Acompañante": "",
}


def crear_template() -> Path:
    """Crea el Excel template y lo guarda en el proyecto."""
    rows = [
        EJEMPLO_COMPLETO,
        EJEMPLO_MINIMO,
    ]
    # Añadir 48 filas vacías para llenar
    for _ in range(48):
        rows.append({c: "" for c in COLUMNAS})

    df = pd.DataFrame(rows, columns=COLUMNAS)
    out_path = PROJECT_ROOT / "Plantilla_Carga_KoboToolbox.xlsx"

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Datos", index=False)

        # Hoja de instrucciones
        inst = pd.DataFrame([
            ["COLUMNA", "DESCRIPCIÓN", "VALORES VÁLIDOS / FORMATO"],
            ["Fecha de Atención", "Obligatorio. Formato YYYY-MM-DD", "Ej: 2026-03-11"],
            ["Nombre del Paciente", "Obligatorio. Mayúsculas como en ID", "Ej: JUAN PÉREZ"],
            ["Sexo", "Obligatorio", "F, M, Femenino, Masculino"],
            ["Edad", "Recomendado. Número", "0 si menor de 1 año"],
            ["Fecha de nacimiento", "Opcional. YYYY-MM-DD", "Se calcula si falta y hay Edad"],
            ["Estado", "Obligatorio. Estado de la brigada", " | ".join(VALORES_ESTADO)],
            ["Lugar", "Recomendado", "Nombre colegio/comunidad/ciudad"],
            ["Modalidad", "Por defecto Móvil", " | ".join(VALORES_MODALIDAD)],
            ["Primera vez o seguimiento", "Por defecto Primera vez", " | ".join(VALORES_FOLLOWUP)],
            ["Servicio que se brinda", "Obligatorio", " | ".join(VALORES_SERVICIO)],
            ["Padecimiento", "Diagnóstico o motivo", "Texto libre"],
            ["Talla (cm)", "En centímetros", "Ej: 170"],
            ["Peso (kg)", "En kilogramos", "Ej: 75"],
            ["¿Entrega Tratamiento?", "Si/No", "Si, No, Sí"],
            ["Insumos Entregados", "Si hubo entrega", "Texto libre"],
            ["¿Se hizo referencia?", "Si/No", "Si, No, Sí"],
            ["¿A dónde?", "Si hay referencia", "Clínica, Segundo Nivel, ONG, etc."],
            ["Motivo Ref.", "Si hay referencia", "Desnutrición, Cirugía, etc."],
            ["Estatus", "Migratorio", " | ".join(VALORES_ESTATUS[:4]) + " ..."],
            ["Acompañante", "Opcional", "Cuidadora mujer, Cuidador hombre, etc."],
        ], columns=["Columna", "Descripción", "Valores / Formato"])
        inst.to_excel(writer, sheet_name="Instrucciones", index=False)

    print(f"Template creado: {out_path}")
    print("  - Hoja 'Datos': 2 filas de ejemplo + 48 vacías para llenar")
    print("  - Hoja 'Instrucciones': valores válidos por columna")
    print("\nPara usar: llena las filas, guarda, sube el archivo en la app y pulsa 'Iniciar carga'.")
    return out_path


if __name__ == "__main__":
    crear_template()
