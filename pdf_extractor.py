#!/usr/bin/env python3
"""
Extrae texto de PDFs (texto nativo o escaneados con OCR).
Convierte el resultado en una estructura que se puede mapear al formulario web.
"""

import re
import sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_text_pdfplumber(pdf_path: Path) -> list[dict]:
    """Extrae texto con pdfplumber (PDF con capa de texto)."""
    if not pdfplumber:
        return []
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            tables = page.extract_tables()
            pages_data.append({
                "page": i + 1,
                "text": text or "",
                "tables": tables or [],
            })
    return pages_data


def extract_text_ocr(pdf_path: Path, lang: str = "spa+eng") -> list[dict]:
    """Extrae texto con OCR (PDF escaneado). Requiere Tesseract y Poppler."""
    if not OCR_AVAILABLE:
        raise ImportError("Instala pdf2image, pytesseract y Pillow. Además: brew install tesseract poppler")
    images = convert_from_path(pdf_path, dpi=200)
    pages_data = []
    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang=lang)
        pages_data.append({"page": i + 1, "text": text or "", "tables": []})
    return pages_data


def extract_from_pdf(pdf_path: Path, force_ocr: bool = False, lang: str = "spa+eng") -> list[dict]:
    """
    Extrae texto del PDF. Usa pdfplumber si hay texto; si está vacío o force_ocr, usa OCR.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"No se encontró: {pdf_path}")

    pages = extract_text_pdfplumber(pdf_path)
    total_text = "".join(p.get("text", "") or "" for p in pages)

    if force_ocr or (not total_text.strip() and OCR_AVAILABLE):
        pages = extract_text_ocr(pdf_path, lang=lang)
    elif not total_text.strip() and not OCR_AVAILABLE:
        print("AVISO: PDF parece escaneado pero OCR no está disponible. Instala: brew install tesseract poppler")

    return pages


def parse_checkboxes(text: str) -> list[str]:
    """Detecta patrones (x) o (X) como casillas marcadas."""
    return re.findall(r"\([xX]\)", text)


def parse_form_fields_heuristic(pages_data: list[dict]) -> dict:
    """
    Parser heurístico: extrae campos conocidos del formulario brigadas ADRA.
    Busca patrones de texto típicos y valores adyacentes.
    """
    full_text = "\n".join(p.get("text", "") or "" for p in pages_data)

    result = {
        "raw_text": full_text,
        "pages": len(pages_data),
        "demograficos": {},
        "consulta": {},
        "identificacion": {},
        "especialidades_marcadas": [],
        "servicios_por_especialidad": {},
    }

    # Patrones comunes
    patterns = {
        "nombre": r"(?:Nombre|nombre)[:\s]*([A-Za-zÀ-ÿ\s]+?)(?=\n|Edad|Fecha|Sexo|$)",
        "edad": r"(?:Edad|edad)[:\s]*(\d+)",
        "fecha": r"(?:Fecha|fecha)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        "sexo": r"[Ss]exo[:\s]*[MH]\s*[\(xX\)]|[MH]\s*\([xX]\)",
        "fecha_nacimiento": r"(?:Fecha de nacimiento|fecha de nacimiento)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        "estatura": r"(?:Estatura|estatura)[:\s]*([\d.,]+)",
        "peso": r"(?:Peso|peso)[:\s]*([\d.,]+\s*kg?)",
        "diagnostico": r"(?:Diagnostico|Diagnóstico|diagnostico)[:\s]*([A-Za-zÀ-ÿ\s]+?)(?=\n|Referencia|$)",
        "motivo_consulta": r"(?:Motivo de la consulta|motivo)[:\s]*([A-Za-zÀ-ÿ\s]+?)(?=\n|Insumos|Diagnostico|$)",
    }

    for key, pat in patterns.items():
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip() if m.lastindex else m.group(0)
            if key in ("nombre",):
                result["identificacion"][key] = val
            elif key in ("edad", "fecha", "sexo"):
                result["identificacion"][key] = val
            elif key in ("fecha_nacimiento", "estatura", "peso"):
                result["demograficos"][key] = val
            elif key in ("motivo_consulta", "diagnostico"):
                result["consulta"][key] = val

    # Especialidades: solo las que tienen (x) en SU sección + extraer diagnóstico y resultados
    esp_config = [
        ("ODONTOLOGÍA", r"ODONTOLOG[IÍ]A"),
        ("FISIOTERAPIA", r"FISIOTERAPIA"),
        ("MEDICINA GENERAL", r"MEDICINA\s+GENERAL"),
        ("OFTALMOLOGÍA", r"OFTALMOLOG[IÍ]A"),
        ("LABORATORIO", r"LABORATORIO"),
    ]
    servicios_por_esp = {}

    for esp_name, esp_pat in esp_config:
        m = re.search(esp_pat, full_text, re.IGNORECASE)
        if not m:
            continue
        start = m.end()
        next_m = re.search(
            r"ODONTOLOG[IÍ]A|FISIOTERAPIA|MEDICINA\s+GENERAL|OFTALMOLOG[IÍ]A|LABORATORIO",
            full_text[start:],
            re.IGNORECASE,
        )
        end = start + next_m.start() if next_m else len(full_text)
        block = full_text[start:end]
        if not re.search(r"\([xX4+]\)", block):
            continue
        result["especialidades_marcadas"].append(esp_name)
        # Extraer diagnóstico/procedimiento de esta fila (palabras tras marcas o entre texto)
        diag = _extract_diagnostico_from_block(block, esp_name)
        res = _extract_resultados_from_block(block, esp_name)
        servicios_por_esp[esp_name] = {"diagnostico": diag, "resultados": res}

    result["servicios_por_especialidad"] = servicios_por_esp
    return result


def _extract_diagnostico_from_block(block: str, especialidad: str) -> str:
    """Extrae diagnóstico/motivo/procedimiento del bloque de una especialidad."""
    block_clean = re.sub(r"\s+", " ", block).strip()
    # Patrones según especialidad
    if "LABORATORIO" in especialidad.upper():
        for m in re.finditer(r"(?:Control|Glucosa|Colesterol|Triglic|HDL|Hiperlip[a-z]*)\s*", block, re.I):
            return m.group(0).strip()
    # Palabras clave de diagnóstico
    keywords = [
        r"Limpieza(?:\s*\+\d*)?", r"Caries", r"Consulta(?:\s*\+?\d*)?", r"C[aá]lculo",
        r"Control(?:\s*\+?\d*)?", r"Dental", r"Dolor\s+espalda", r"Lesi[oó]n\s+(?:espalda|musc)",
        r"Lumbalgia", r"Presbicia", r"Oftalmolog[ií]a", r"Gripe", r"Otitis", r"Amigdalitis",
        r"Hiperlipidemia", r"Micosis", r"Parasit", r"Med\.?\s*Gral", r"Tratamiento\s*[12]",
    ]
    for kw in keywords:
        m = re.search(kw, block, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    # Fallback: primera línea con contenido sustancial
    for line in block.split("\n"):
        line = line.strip()
        if len(line) > 3 and not re.match(r"^[\(\)xX0-9\s]+$", line):
            return line[:80]
    return ""


def _extract_resultados_from_block(block: str, especialidad: str) -> str:
    """Extrae resultados lab / insumos del bloque."""
    if "LABORATORIO" in especialidad.upper():
        # G:111, C:180, T:167, H:51
        m = re.search(r"G\s*:\s*[\d.,]+\s*[,\s]?\s*C\s*:\s*[\d.,]+\s*[,\s]?\s*T\s*:\s*[\d.,]+\s*[,\s]?\s*H\s*:\s*[\d.,]+", block)
        if m:
            return m.group(0)
        m = re.search(r"(?:Glucosa|G)\s*(?:marcada|:)?\s*[\d.,]*", block, re.I)
        if m:
            return m.group(0).strip()
    # Dental: Kit limpieza, Consulta marcada
    if "ODONTOLOG" in especialidad.upper():
        parts = []
        if re.search(r"kit\s*(?:limpieza\s*)?dental", block, re.I):
            parts.append("Kit limpieza dental")
        if re.search(r"consulta\s*marcada", block, re.I):
            parts.append("Consulta marcada")
        if re.search(r"limpieza", block, re.I):
            parts.append("Limpieza")
        if parts:
            return ", ".join(parts)
    # Oftalmología: Lentes, Medicamentos
    if "OFTALMOLOG" in especialidad.upper():
        parts = []
        if re.search(r"lentes", block, re.I):
            parts.append("Lentes")
        m = re.search(r"(\d+)\s*medicamentos?", block, re.I)
        if m:
            parts.append(m.group(0))
        elif re.search(r"medicamentos?", block, re.I):
            parts.append("Medicamentos")
        if parts:
            return ", ".join(parts)
    # Fisioterapia: Paracetamol, Tratamiento 1/2
    if "FISIOTERAPIA" in especialidad.upper():
        m = re.search(r"tratamiento\s*[12]", block, re.I)
        if m:
            return m.group(0)
        m = re.search(r"paracetamol|ibuprofeno", block, re.I)
        if m:
            return m.group(0)
    # Medicina General: Medicamentos
    if "MEDICINA" in especialidad.upper():
        m = re.search(r"(\d+)\s*medicamentos?", block, re.I)
        if m:
            return m.group(0)
        if re.search(r"medicamentos?", block, re.I):
            return "Medicamentos"
    return ""


def _normalize_sex(sex_str: str) -> str:
    """M/H en formulario; F del Excel se mapea a F (femenino), H = masculino."""
    s = (sex_str or "").strip().upper()[:1]
    if s in ("F", "M", "H"):
        return s
    return ""


def _format_fecha(fecha_str: str) -> str:
    """Convierte DD/MM/YY a YYYY-MM-DD para consistencia."""
    s = (fecha_str or "").strip()
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", s)
    if m:
        d, mes, y = m.groups()
        y = "20" + y if len(y) == 2 else y
        return f"{y}-{mes.zfill(2)}-{d.zfill(2)}"
    return s


def extract_and_to_records(pdf_path: Path, force_ocr: bool = False, per_page: bool = True) -> tuple[list[dict], dict]:
    """
    ETL: Extrae PDF y genera registros en formato "Reorganización por Especialidad".
    1 paciente con N especialidades marcadas → N filas (clonación + datos por especialidad).
    Si per_page=True y hay varias páginas, procesa cada página como un paciente.

    Returns:
        (records, parsed): records con columnas NAME, Fecha_de_atenci_n, SEX, etc.
    """
    pages = extract_from_pdf(pdf_path, force_ocr=force_ocr)
    all_records = []
    parsed_agg = {"pages": len(pages), "especialidades_marcadas": [], "servicios_por_especialidad": {}}

    parsed_out: dict = {}
    if per_page and len(pages) > 1:
        for i, p in enumerate(pages):
            page_data = [p]
            parsed = parse_form_fields_heuristic(page_data)
            recs = _build_records_from_parsed(parsed)
            if recs:
                all_records.extend(recs)
        parsed_out = {"pages": len(pages), "processed_per_page": True}
    else:
        parsed = parse_form_fields_heuristic(pages)
        all_records = _build_records_from_parsed(parsed)
        parsed_out = {k: v for k, v in parsed.items() if k != "raw_text"}

    if not all_records:
        parsed = parse_form_fields_heuristic(pages)
        all_records = _build_records_from_parsed(parsed)
        parsed_out = {k: v for k, v in parsed.items() if k != "raw_text"}
        if "pages" not in parsed_out:
            parsed_out["pages"] = len(pages)

    return all_records, parsed_out


def _build_records_from_parsed(parsed: dict) -> list[dict]:
    id_ = parsed.get("identificacion", {})
    demo = parsed.get("demograficos", {})
    cons = parsed.get("consulta", {})
    especialidades = parsed.get("especialidades_marcadas", [])
    servicios_por_esp = parsed.get("servicios_por_especialidad", {})

    # Evitar duplicados de especialidad
    seen = set()
    uniq = []
    for e in especialidades:
        key = e.upper().replace("Ó", "O").replace("Í", "I")
        if key not in seen:
            seen.add(key)
            uniq.append(e)

    if not uniq:
        uniq = ["General"]

    nombre = str(id_.get("nombre", "")).strip()
    edad = str(id_.get("edad", "")).strip()
    sexo_raw = str(id_.get("sexo", "")).strip()
    sexo = _normalize_sex(sexo_raw) or ("F" if "F" in sexo_raw.upper() else "H")
    fecha = _format_fecha(str(id_.get("fecha", "")))
    estatura = str(demo.get("estatura", "")).strip()
    peso = str(demo.get("peso", "")).replace("kg", "").strip()
    talla_peso = f"{estatura} / {peso}" if estatura or peso else ""
    diag_global = str(cons.get("diagnostico", "")).strip() or str(cons.get("motivo_consulta", "")).strip()

    records = []
    for esp in uniq:
        info = servicios_por_esp.get(esp, {})
        diag_esp = info.get("diagnostico", "") or diag_global
        res_esp = info.get("resultados", "")

        rec = {
            "NAME": nombre,
            "AGE": edad,
            "SEX": sexo,
            "Fecha_de_atenci_n": fecha,
            "HEI": estatura,
            "WEI": peso,
            "Servicio_que_se_brinda": esp,
            "Diagnostico_Motivo": diag_esp,
            "Resultados_Lab_Insumos": res_esp,
        }
        records.append(rec)

    return records


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python pdf_extractor.py <ruta_al.pdf> [--ocr] [--json]")
        print("  --ocr: forzar OCR aunque el PDF tenga texto")
        print("  --json: guardar resultado estructurado en JSON")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    force_ocr = "--ocr" in sys.argv
    save_json = "--json" in sys.argv

    print(f"Extrayendo de: {pdf_path}")
    try:
        pages = extract_from_pdf(pdf_path, force_ocr=force_ocr)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Páginas procesadas: {len(pages)}")
    total_chars = sum(len(p.get("text", "")) for p in pages)
    print(f"Caracteres extraídos: {total_chars}")

    # Guardar texto crudo
    output_txt = pdf_path.parent / f"{pdf_path.stem}_extraido.txt"
    with open(output_txt, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(f"--- Página {p['page']} ---\n")
            f.write(p.get("text", "") or "")
            f.write("\n\n")
    print(f"Texto guardado en: {output_txt}")

    # Parser heurístico
    parsed = parse_form_fields_heuristic(pages)
    # Quitar raw_text para salida compacta
    out = {k: v for k, v in parsed.items() if k != "raw_text"}
    print("\n--- Campos detectados (heurístico) ---")
    for k, v in out.items():
        if isinstance(v, dict) and v:
            print(f"  {k}: {v}")
        elif k == "especialidades_marcadas" and v:
            print(f"  especialidades_marcadas: {v}")

    if save_json:
        import json
        output_json = pdf_path.parent / f"{pdf_path.stem}_estructurado.json"
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"\nJSON guardado en: {output_json}")


if __name__ == "__main__":
    main()
