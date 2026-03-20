#!/usr/bin/env python3
"""
Extrae la estructura del formulario Enketo (name, data-name, data-path)
y genera un mapping.yaml plantilla para completar manualmente.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import FORM_URL, HEADLESS

PROJECT_ROOT = Path(__file__).resolve().parent
MAPPING_OUTPUT = PROJECT_ROOT / "mapping_discovered.yaml"
CAMPOS_REPORT = PROJECT_ROOT / "CAMPOS_FORMULARIO_CON_ETIQUETAS.md"


def discover_form_fields() -> tuple[dict[str, str], list[dict]]:
    """Abre el formulario, extrae los campos. Retorna (fields_dict, items_con_label)."""
    fields = {}
    items_with_labels = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        page.set_default_timeout(30000)

        try:
            page.goto(FORM_URL, wait_until="networkidle")
            page.wait_for_load_state("domcontentloaded")

            js_extract = """
            () => {
                const results = [];
                const selectors = [
                    'input[name]', 'textarea[name]', 'select[name]',
                    '[data-name]', '[data-path]'
                ];
                const seen = new Set();
                const JUNK_NAMES = new Set([
                    'search', 'lat', 'long', 'alt', 'acc',
                ]);
                for (const sel of selectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        const name = el.getAttribute('name') || el.getAttribute('data-name') || el.getAttribute('data-path');
                        if (!name || seen.has(name)) return;
                        // Filtrar elementos basura: IDs numéricos de cascading selects,
                        // controles de mapa (leaflet), y elementos internos de Enketo
                        if (/^\\d+(\\.\\d+)?$/.test(name)) return;
                        if (name.startsWith('leaflet-')) return;
                        if (JUNK_NAMES.has(name)) return;
                        if (name.startsWith('__') || name === 'undefined') return;
                        seen.add(name);
                        let label = '';
                        const question = el.closest('.question, [role="group"], .or-appearance');
                        if (question) {
                            const labelEl = question.querySelector('label, .question-label, .or-appearance-label');
                            if (labelEl) label = (labelEl.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 60);
                        }
                        const short = name.split('/').pop() || name;
                        results.push({ name, short, label, type: el.type || el.tagName });
                    });
                }
                return results;
            }
            """
            raw = page.evaluate(js_extract)
            if isinstance(raw, list):
                for item in raw:
                    path = item.get("name", "")
                    short = item.get("short", path.split("/")[-1] if "/" in path else path)
                    label = item.get("label", "")
                    fields[short] = path
                    items_with_labels.append({"short": short, "path": path, "label": label})

        finally:
            browser.close()

    return fields, items_with_labels


def main() -> None:
    """Ejecuta el discovery y guarda mapping_discovered.yaml y reporte de etiquetas."""
    print(f"Conectando a {FORM_URL}...")
    try:
        fields, items = discover_form_fields()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not fields:
        print("No se encontraron campos. Verifica la URL y que el formulario cargue correctamente.")
        sys.exit(1)

    # YAML de mapeo
    lines = [
        "# Mapeo generado por discover_form.py",
        "# Ajusta los nombres de la izquierda para que coincidan con las columnas de tu Excel",
        "# Los valores de la derecha son los paths del formulario Enketo",
        "",
    ]
    import re as _re
    for col, path in sorted(fields.items()):
        if col.startswith("__") or col in ("acc", "lat", "long", "alt", "search"):
            continue
        if _re.match(r"^\d+(\.\d+)?$", col):
            continue
        if col.startswith("leaflet-"):
            continue
        lines.append(f'{col}: "{path}"')

    with open(MAPPING_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Reporte con etiquetas visibles (para relacionar con columnas Excel)
    md_lines = [
        "# Campos del formulario web con etiquetas visibles",
        "",
        "| Etiqueta visible | Nombre técnico | Columna Excel sugerida |",
        "|------------------|----------------|------------------------|",
    ]
    excel_suggestions = {
        "NAME": "Nombre del Paciente",
        "Fecha_de_atenci_n": "Fecha / Fecha atención",
        "SEX": "Sexo",
        "Servicio_que_se_brinda": "Servicio Brindado",
        "HEI": "Talla (de Talla/Peso)",
        "WEI": "Peso (de Talla/Peso)",
        "dxesp": "Diagnóstico / Motivo",
        "Especificar_lo_que_se_entrega_": "Resultados Lab / Insumos",
    }
    for item in sorted(items, key=lambda x: (x["label"] or "", x["short"])):
        short = item["short"]
        label = (item["label"] or "—")[:40]
        sug = excel_suggestions.get(short, short)
        md_lines.append(f"| {label} | {short} | {sug} |")

    with open(CAMPOS_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Se encontraron {len(fields)} campos.")
    print(f"Mapeo guardado en: {MAPPING_OUTPUT}")
    print(f"Tabla con etiquetas en: {CAMPOS_REPORT}")


if __name__ == "__main__":
    main()
