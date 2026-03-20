"""
Carga Excel en formato "Consolidación de Datos de Brigada Médica" (y variantes)
y transforma a columnas internas usadas por el mapeo KoboToolbox.
"""

import re
from pathlib import Path

import pandas as pd


# Columnas internas (passthrough si el Excel ya las tiene)
INTERNAL_COLUMNS = {
    "NAME", "Fecha_de_atenci_n", "SEX", "Servicio_que_se_brinda", "Diagnostico_Motivo",
    "HEI", "WEI", "Resultados_Lab_Insumos", "ME_ML", "Tratamiento", "Plan_de_Tratamiento",
    "Estado_paciente",
    "esp_odontologia", "esp_fisioterapia", "esp_medicina_general",
    "esp_oftalmologia", "esp_laboratorio",
}


def _normalize_excel_column_name(name: str) -> str:
    """Normaliza nombre de columna para búsqueda: quita asteriscos y espacios extra."""
    if not name:
        return ""
    s = str(name).strip().rstrip("*").strip()
    return s


# Mapeo: nombre columna en Excel → nombre columna interno (formulario KoboToolbox)
# Soporta: Consolidación, Brigada de Salud, Plantilla_Brigadas_Salud_Clinicas (con o sin * en encabezados)
EXCEL_TO_INTERNAL = {
    # --- Consolidación de Datos de Brigada Médica ---
    "Fecha de Atención": "Fecha_de_atenci_n",
    "Nombre del Paciente": "NAME",
    "Servicio que se brinda": "Servicio_que_se_brinda",
    "Padecimiento": "Diagnostico_Motivo",
    "Talla (cm)": "HEI",
    "Peso (kg)": "WEI",
    "¿Entrega Tratamiento?": "entrega_tx",
    "Insumos Entregados": "Resultados_Lab_Insumos",
    "¿Ref?": "Referencia",
    "¿A dónde?": "Referencia_donde",
    "Motivo Ref.": "Motivo_referencia",
    # --- Brigada de Salud: Registro de Pacientes ---
    "Servicio": "Servicio_que_se_brinda",
    "¿Entrega?": "entrega_tx",
    "Insumos": "Resultados_Lab_Insumos",
    "Motivo Ref": "Motivo_referencia",
    "Edad": "AGE",
    "Sexo": "SEX",
    "Acompañante": "CGR",
    "Modalidad": "Modalidad_de_la_atenci_n",
    "Estado": "Estado_brigada",
    "Consent.": "CONS1",
    "Estatus": "estatus_migra",
    "Minoría": "_Pertenece_a_alguna_minor_a_t",
    "Asesoría": "ASESPREV",
    # --- Reorganización / formato anterior ---
    "Nombre": "NAME",
    "NAME": "NAME",
    "AGE": "AGE",
    "Fecha": "Fecha_de_atenci_n",
    "Fecha de atención": "Fecha_de_atenci_n",
    "Fecha_de_atenci_n": "Fecha_de_atenci_n",
    "Fecha de nacimiento": "DOB",
    "Fecha nacimiento": "DOB",
    "DOB": "DOB",
    "SEX": "SEX",
    "Consentimiento": "CONS1",
    "CONS1": "CONS1",
    "HEI": "HEI",
    "WEI": "WEI",
    "Diagn_stico": "Diagn_stico",
    "Estado brigada": "Estado_brigada",
    "Estado_brigada": "Estado_brigada",
    "Lugar": "Lugar",
    "Ubicacion_geografica": "Ubicacion_geografica",
    "Lugar de atención": "Lugar",
    "PLACE": "Lugar",
    "Ubicación geográfica": "Ubicacion_geografica",
    "Primera vez o seguimiento": "followup",
    "followup": "followup",
    "Referencia": "Referencia",
    "Se hizo referencia": "Referencia",
    "Referencia dónde": "Referencia_donde",
    "Referencia_donde": "Referencia_donde",
    "Motivo referencia": "Motivo_referencia",
    "Motivo_referencia": "Motivo_referencia",
    "Servicio Brindado": "Servicio_que_se_brinda",
    "Especialidad": "Servicio_que_se_brinda",
    "Diagnóstico / Motivo": "Diagnostico_Motivo",
    "Diagnóstico / motivo": "Diagnostico_Motivo",
    "Diagnostico_Motivo": "Diagnostico_Motivo",
    "Talla / Peso": "Talla_Peso_raw",  # Se separa en HEI y WEI
    "Talla / peso": "Talla_Peso_raw",
    "Resultados Lab / Insumos": "Resultados_Lab_Insumos",
    "Resultados Lab / insumos": "Resultados_Lab_Insumos",
    "Resultados_Lab_Insumos": "Resultados_Lab_Insumos",
    # Passthrough para columnas ya en formato interno (p. ej. tras confirmar)
    "entrega_tx": "entrega_tx",
    "estatus_migra": "estatus_migra",
    "Modalidad_de_la_atenci_n": "Modalidad_de_la_atenci_n",
    # --- Plantilla_Brigadas_Salud_Clinicas (encabezados con * y variantes) ---
    "Nombre del Paciente*": "NAME",
    "Fecha de atención": "Fecha_de_atenci_n",
    "Toma consentimiento inicial": "CONS1",
    "Toma de consentimiento antes de iniciar la consulta": "CONS1",
    "Lugar de atención": "Lugar",
    "Modalidad de la atención": "Modalidad_de_la_atenci_n",
    "Estado": "Estado_brigada",
    "Primera vez o Seguimiento": "followup",
    "Entrega de Insumos": "entrega_tx",
    "Servicio que se brinda": "Servicio_que_se_brinda",
    "Nacionalidad": "NAT",
    "Estatus migratorio": "estatus_migra",
    "Sexo": "SEX",
    "Fecha de nacimiento": "DOB",
    "Edad": "AGE",
    "Talla (cm)": "HEI",
    "Peso (kg)": "WEI",
    "Padecimiento médico actual": "Diagnostico_Motivo",
    "Motivo de la consulta": "Diagnostico_Motivo",
    "Diagnósticos": "Diagnostico_Motivo",
    "Diagnosticos": "Diagnostico_Motivo",
    "Entrega de tratamiento": "entrega_tx",
    "¿Se hizo entrega de tratamiento/artículos al beneficiario o beneficiaria?": "entrega_tx",
    "¿Se hizo referencia?": "Referencia",
    "Consentimiento informado verbal": "CONS1",
    # --- Insumos entregados (plantilla nueva) ---
    "Insumos Entregados": "Resultados_Lab_Insumos",
    "Insumos entregados": "Resultados_Lab_Insumos",
    # --- Asesoría en módulos ---
    "¿Se le ha brindado asesoría en uno de los módulos el día de hoy?": "ASESPREV",
    "Asesoría en módulos": "ASESPREV",
    "Asesoria en modulos": "ASESPREV",
    # --- Pertenece a minoría étnica ---
    "¿Pertenece a alguna minoría étnica?": "_Pertenece_a_alguna_minor_a_t",
    "Pertenece a alguna minoría étnica": "_Pertenece_a_alguna_minor_a_t",
    "Minoria etnica": "_Pertenece_a_alguna_minor_a_t",
    # --- Lugar de Atención por estado (plantilla con columnas separadas por estado) ---
    # Solo una tendrá valor por fila (la del estado correspondiente al paciente)
    "Lugar de Atención: Sonora": "Lugar",
    "Lugar de atención: Sonora": "Lugar",
    "Lugar de Atención: Nuevo León": "Lugar",
    "Lugar de atención: Nuevo León": "Lugar",
    "Lugar de Atención: Nuevo Leon": "Lugar",
    "Lugar de atención: Nuevo Leon": "Lugar",
    "Lugar de Atención: Chihuahua": "Lugar",
    "Lugar de atención: Chihuahua": "Lugar",
    "Lugar de Atención: Otro": "Lugar",
    "Lugar de atención: Otro": "Lugar",
    "Lugar de Atención: Baja California": "Lugar",
    "Lugar de atención: Baja California": "Lugar",
    "Lugar de Atención: Baja California Sur": "Lugar",
    "Lugar de atención: Baja California Sur": "Lugar",
    # --- Embarazo / Lactancia ---
    "¿Mujer embarazada o en periodo de lactancia?": "ME_ML",
    "Mujer embarazada o en periodo de lactancia": "ME_ML",
    "Embarazada o lactancia": "ME_ML",
    "Embarazo/Lactancia": "ME_ML",
    "Embarazo / Lactancia": "ME_ML",
    "Embarazo": "ME_ML",
    "ME_ML": "ME_ML",
    # --- Estado del paciente (diferente de Estado_brigada que es el lugar de la brigada) ---
    "Estado paciente": "Estado_paciente",
    "Estado del paciente": "Estado_paciente",
    "Estado_paciente": "Estado_paciente",
    "Estado (paciente)": "Estado_paciente",
    "Estado.1": "Estado_paciente",   # pandas renombra la 2ª columna "Estado" → "Estado.1"
    # --- Tratamiento ---
    "Tratamiento": "Tratamiento",
    "Tratamiento (Si Oftalmología brinda lentes especificar graduación de ojo derecho/izquierdo.)": "Tratamiento",
    "Tratamiento (Si Oftalmología brinda lentes especificar graduación de ojo derecho/izquierdo)": "Tratamiento",
    "Tx": "Tratamiento",
    "TX": "Tratamiento",
    # --- Plan de tratamiento (texto libre en Kobo) ---
    "Plan de Tratamiento": "Plan_de_Tratamiento",
    "Plan de tratamiento": "Plan_de_Tratamiento",
    "Plan_de_Tratamiento": "Plan_de_Tratamiento",
    # --- ¿Requiere anteojos? ---
    "¿Requiere anteojos?": "_Requiere_anteojos",
    "Requiere anteojos": "_Requiere_anteojos",
    "Requiere anteojos?": "_Requiere_anteojos",
    "_Requiere_anteojos": "_Requiere_anteojos",
    "Anteojos": "_Requiere_anteojos",
    "anteojos": "_Requiere_anteojos",
    # --- Discapacidad ---
    "Discapacidad": "Discapacidad",
    "Discapacidades": "Discapacidad",
    "Tipo de discapacidad": "Discapacidad",
    "Tipo discapacidad": "Discapacidad",
    "Indicar si el paciente tiene alguna de las siguientes discapacidades": "Discapacidad",
    "Indicar discapacidad": "Discapacidad",
    "Latitud": "lat",
    "Longitud": "long",
    "Altitud (m)": "alt",
    "Precisión (m)": "acc",
    # --- Especialidades del formulario físico (hoja de servicio) ---
    # Permiten detectar automáticamente Servicio_que_se_brinda y ASESPREV
    # cuando las columnas reflejan las especialidades marcadas en el formulario manual.
    "ODONTOLOGÍA": "esp_odontologia",
    "ODONTOLOGIA": "esp_odontologia",
    "Odontología": "esp_odontologia",
    "Odontologia": "esp_odontologia",
    "DENTAL": "esp_odontologia",
    "Dental": "esp_odontologia",
    "FISIOTERAPIA": "esp_fisioterapia",
    "Fisioterapia": "esp_fisioterapia",
    "MEDICINA GENERAL": "esp_medicina_general",
    "Medicina General": "esp_medicina_general",
    "Medicina general": "esp_medicina_general",
    "MED. GENERAL": "esp_medicina_general",
    "OFTALMOLOGÍA": "esp_oftalmologia",
    "OFTALMOLOGIA": "esp_oftalmologia",
    "Oftalmología": "esp_oftalmologia",
    "Oftalmologia": "esp_oftalmologia",
    "LABORATORIO CLÍNICO": "esp_laboratorio",
    "LABORATORIO CLINICO": "esp_laboratorio",
    "LABORATORIO": "esp_laboratorio",
    "Laboratorio Clínico": "esp_laboratorio",
    "Laboratorio Clinico": "esp_laboratorio",
    "Laboratorio": "esp_laboratorio",
    "Laboratorios": "esp_laboratorio",
    "LABORATORIOS": "esp_laboratorio",
}
# Claves que pueden venir de la plantilla y deben mostrarse en la tabla (unión con OUTPUT_COLUMNS)
OUTPUT_COLUMNS_EXTRA = ["NAT", "lat", "long", "alt", "acc"]

# Orden de columnas en la salida (para consistencia)
OUTPUT_COLUMNS = [
    "NAME",
    "Fecha_de_atenci_n",
    "SEX",
    "AGE",
    "DOB",
    "Estado_brigada",
    "Lugar",
    "Servicio_que_se_brinda",
    "Diagnostico_Motivo",
    "HEI",
    "WEI",
    "Resultados_Lab_Insumos",
    "entrega_tx",
    "Referencia",
    "Referencia_donde",
    "Motivo_referencia",
    "CGR",
    "estatus_migra",
    "followup",
    "ME_ML",
    "Discapacidad",
    "Tratamiento",
    "Plan_de_Tratamiento",
    "Estado_paciente",
    # Columnas de especialidad del formulario físico (para detección automática del servicio)
    "esp_medicina_general",
    "esp_odontologia",
    "esp_fisioterapia",
    "esp_oftalmologia",
    "esp_laboratorio",
]


def _split_talla_peso(val: str) -> tuple[str, str]:
    """
    Separa "1.67 / 63" en HEI (estatura) y WEI (peso).
    Acepta variaciones: "1.67/63", "1.67 - 63", etc.
    """
    s = str(val or "").strip()
    if not s:
        return "", ""
    # Buscar patrones como 1.67 / 63, 1.67/63, 1.67 - 63
    m = re.match(r"([\d.,]+)\s*[/\-]\s*([\d.,]+)", s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Si no hay separador, intentar usar como estatura
    if re.match(r"^[\d.,]+$", s):
        return s, ""
    return s, ""


def _normalize_fecha(val: str) -> str:
    """Convierte 2026-02-17 00:00:00 o DD/MM/YYYY a YYYY-MM-DD."""
    s = str(val or "").strip()
    if not s:
        return ""
    # pandas devuelve "2026-02-17 00:00:00" o similar
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", s)
    if m:
        d, mes, y = m.groups()
        y = "20" + y if len(y) == 2 else y
        return f"{y}-{mes.zfill(2)}-{d.zfill(2)}"
    return s


def _normalize_sex(val: str) -> str:
    """M/H en formulario; F, M, masculino, femenino, etc."""
    s = str(val or "").strip().upper()[:1]
    if s in ("F", "M"):
        return "F" if s == "F" else "H"
    if "FEM" in str(val or "").upper() or "MUJER" in str(val or "").upper():
        return "F"
    if "MASC" in str(val or "").upper() or "HOMBRE" in str(val or "").upper():
        return "H"
    return s if s in ("F", "H", "M") else ""


def _normalize_si_no(val: str) -> str:
    """Sí/No → 1/0 para formulario."""
    s = str(val or "").strip().lower()
    if s in ("sí", "si", "yes", "1", "s"):
        return "1"
    if s in ("no", "n", "0"):
        return "0"
    return ""


def _normalize_modalidad(val: str) -> str:
    """Móvil, movil, etc. → movil."""
    s = str(val or "").strip().lower()
    if "móvil" in s or "movil" in s or "mobile" in s:
        return "movil"
    return s or ""


def load_source_dataframe(path: Path, sheet_name: int | str = 0) -> pd.DataFrame:
    """
    Carga .xlsx (openpyxl) o .csv en un DataFrame de texto.

    CSV: utf-8-sig (BOM), utf-8 o latin-1; separador detectado (coma, punto y coma, etc.).
    """
    ext = path.suffix.lower()
    if ext == ".csv":
        last_err: Exception | None = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(
                    path,
                    dtype=str,
                    encoding=encoding,
                    sep=None,
                    engine="python",
                )
            except UnicodeDecodeError as e:
                last_err = e
        if last_err:
            raise last_err
        raise ValueError("No se pudo decodificar el CSV")
    return pd.read_excel(path, sheet_name=sheet_name, dtype=str, engine="openpyxl")


def load_excel_to_records(
    excel_path: Path,
    sheet_name: int | str = 0,
) -> list[dict[str, str]]:
    """
    Carga Excel (.xlsx) o CSV y transforma a registros con columnas internas.

    Args:
        excel_path: Ruta al archivo .xlsx o .csv
        sheet_name: Hoja a leer (0 = primera); solo aplica a Excel

    Returns:
        Lista de diccionarios con claves: NAME, Fecha_de_atenci_n, SEX, etc.
    """
    df = load_source_dataframe(excel_path, sheet_name=sheet_name)
    df = df.fillna("")
    df.columns = [str(c).strip() for c in df.columns]

    records = []
    all_columns = list(OUTPUT_COLUMNS) + [c for c in OUTPUT_COLUMNS_EXTRA if c not in OUTPUT_COLUMNS]
    for _, row in df.iterrows():
        rec = {col: "" for col in all_columns}

        for excel_col, value in row.items():
            value = "" if pd.isna(value) else str(value).strip()
            col_stripped = str(excel_col).strip()
            # Plantilla usa encabezados con * (ej. "Fecha de atención*"); buscar con y sin *
            internal = EXCEL_TO_INTERNAL.get(col_stripped) or EXCEL_TO_INTERNAL.get(
                _normalize_excel_column_name(col_stripped)
            )
            if internal is None and col_stripped in INTERNAL_COLUMNS:
                internal = col_stripped
            if internal is None:
                continue

            if internal == "NAME":
                # Quitar cualquier fecha (YYYY-MM-DD) que pueda venir concatenada al final
                clean_name = re.sub(r'[\s\-]?\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*$', '', value).strip()
                clean_name = re.sub(r'[\s\-]?\d{1,2}[-/]\d{1,2}[-/]\d{4}\s*$', '', clean_name).strip()
                rec["NAME"] = clean_name
            elif internal == "Fecha_de_atenci_n":
                rec["Fecha_de_atenci_n"] = _normalize_fecha(value)
            elif internal == "SEX":
                rec["SEX"] = _normalize_sex(value) or value
            elif internal == "Servicio_que_se_brinda":
                rec["Servicio_que_se_brinda"] = value
            elif internal == "Diagnostico_Motivo":
                if value:  # no sobreescribir con vacío (ej. columna "Diagnósticos" NaN borra "Padecimiento médico actual")
                    rec["Diagnostico_Motivo"] = value
            elif internal == "Talla_Peso_raw":
                hei, wei = _split_talla_peso(value)
                rec["HEI"] = hei
                rec["WEI"] = wei
            elif internal == "HEI":
                rec["HEI"] = str(value).replace(",", ".") if value else ""
            elif internal == "WEI":
                rec["WEI"] = str(value).replace(",", ".") if value else ""
            elif internal == "Resultados_Lab_Insumos":
                rec["Resultados_Lab_Insumos"] = value
            elif internal == "Estado_brigada":
                rec["Estado_brigada"] = value
            elif internal == "Lugar":
                if value:  # solo sobreescribir si hay valor (columnas lugar por estado son mutuamente excluyentes)
                    rec["Lugar"] = value
            elif internal == "DOB":
                rec["DOB"] = _normalize_fecha(value)
            elif internal == "AGE":
                rec["AGE"] = value
            elif internal == "Ubicacion_geografica":
                rec["Ubicacion_geografica"] = value
            elif internal == "followup":
                rec["followup"] = value
            elif internal == "Referencia":
                rec["Referencia"] = value
            elif internal == "Referencia_donde":
                rec["Referencia_donde"] = value
            elif internal == "Motivo_referencia":
                rec["Motivo_referencia"] = value
            elif internal == "entrega_tx":
                rec["entrega_tx"] = _normalize_si_no(value) or value
            elif internal == "CGR":
                rec["CGR"] = value  # Acompañante: Cuidadora mujer, etc.
            elif internal == "estatus_migra":
                rec["estatus_migra"] = value  # Ciudadano Mex, etc.
            elif internal == "_Pertenece_a_alguna_minor_a_t":
                rec["_Pertenece_a_alguna_minor_a_t"] = _normalize_si_no(value) or value
            elif internal == "Modalidad_de_la_atenci_n":
                rec["Modalidad_de_la_atenci_n"] = _normalize_modalidad(value) or value
            elif internal == "ME_ML":
                rec["ME_ML"] = value
            elif internal == "Discapacidad":
                rec["Discapacidad"] = value
            elif internal == "Tratamiento":
                rec["Tratamiento"] = value
            elif internal == "Plan_de_Tratamiento":
                rec["Plan_de_Tratamiento"] = value
            elif internal == "Estado_paciente":
                rec["Estado_paciente"] = value
            elif internal == "CONS1":
                rec["CONS1"] = _normalize_si_no(value) if value else rec.get("CONS1", "")
            elif internal in ("esp_odontologia", "esp_fisioterapia", "esp_medicina_general",
                              "esp_oftalmologia", "esp_laboratorio"):
                # Columnas de especialidad del formulario físico:
                # solo sobreescribir si el valor nuevo es más informativo
                # (no borrar un valor ya marcado con un vacío o cero)
                existing = rec.get(internal, "")
                if value and value not in ("0", ""):
                    rec[internal] = value
                elif not existing:
                    rec[internal] = value
            else:
                # Cualquier otra columna mapeada (NAT, lat, long, alt, acc, etc.)
                rec[internal] = value

        records.append(rec)

    return records


VALID_SEX_VALUES = {"F", "H", "M", "FEMENINO", "MASCULINO", "FEMALE", "MALE"}
VALID_FOLLOWUP_VALUES = {"primera vez", "seguimiento", "atención única", "atencion unica", "entrega de insumos", "1", "2", "3", "4"}
VALID_SERVICES = {"medicina general", "dental", "fisioterapia", "oftalmología", "oftalmologia", "laboratorios"}


def validate_records(records: list[dict[str, str]]) -> dict:
    """
    Valida registros contra los requisitos del formulario.

    Comprueba:
    - Campos obligatorios vacíos (NAME, Fecha_de_atenci_n, SEX, Servicio_que_se_brinda)
    - Valores inválidos (SEX fuera de F/H, Servicio no reconocido)
    - Filas duplicadas por combinación NAME + Fecha_de_atenci_n
    - Campos recomendados vacíos (AGE, Estado_brigada, Lugar, etc.)

    Retorna: { valid: int, with_warnings: int, errors: [...], warnings: [...], duplicates: [...] }
    """
    required = ["NAME", "Fecha_de_atenci_n", "SEX", "Servicio_que_se_brinda"]
    recommended = ["AGE", "Estado_brigada", "Lugar", "Diagnostico_Motivo", "HEI", "WEI"]
    errors = []
    warnings = []
    duplicates = []
    valid = 0
    with_warnings = 0

    # Detectar duplicados por NAME + Fecha_de_atenci_n
    seen_keys: dict[tuple, list[int]] = {}
    for i, rec in enumerate(records):
        key = (
            str(rec.get("NAME", "")).strip().lower(),
            str(rec.get("Fecha_de_atenci_n", "")).strip(),
        )
        if key[0] or key[1]:
            seen_keys.setdefault(key, []).append(i + 1)
    for key, rows in seen_keys.items():
        if len(rows) > 1:
            duplicates.append({
                "nombre": key[0],
                "fecha": key[1],
                "filas": rows,
            })

    for i, rec in enumerate(records):
        row = i + 1
        row_errors = []
        row_warnings = []

        # Campos obligatorios vacíos
        missing_req = [f for f in required if not str(rec.get(f, "")).strip()]
        if missing_req:
            row_errors.append(f"Faltan campos obligatorios: {', '.join(missing_req)}")

        # Validar valores de SEX
        sex_val = str(rec.get("SEX", "")).strip().upper()
        if sex_val and sex_val not in VALID_SEX_VALUES:
            row_warnings.append(f"SEX '{sex_val}' no reconocido (usa F o H)")

        # Validar Servicio_que_se_brinda
        svc_val = str(rec.get("Servicio_que_se_brinda", "")).strip().lower()
        if svc_val and svc_val not in VALID_SERVICES:
            row_warnings.append(f"Servicio '{svc_val}' no está en la lista estándar")

        # Validar formato de fecha (YYYY-MM-DD)
        fecha_val = str(rec.get("Fecha_de_atenci_n", "")).strip()
        if fecha_val and not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha_val):
            row_warnings.append(f"Fecha '{fecha_val}' no está en formato YYYY-MM-DD")

        # Campos recomendados vacíos
        missing_rec = [f for f in recommended if not str(rec.get(f, "")).strip()]

        if row_errors:
            errors.append({"fila": row, "mensaje": "; ".join(row_errors)})
        else:
            valid += 1

        if row_warnings or missing_rec:
            with_warnings += 1
            warn_parts = row_warnings[:]
            if missing_rec:
                warn_parts.append(f"Sin: {', '.join(missing_rec[:3])}{'...' if len(missing_rec) > 3 else ''}")
            if len(warnings) < 30:
                warnings.append({"fila": row, "mensaje": "; ".join(warn_parts)})

    return {
        "valid": valid,
        "with_warnings": with_warnings,
        "total": len(records),
        "errors": errors[:30],
        "warnings": warnings,
        "duplicates": duplicates[:10],
    }
