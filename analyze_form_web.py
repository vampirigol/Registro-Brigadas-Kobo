#!/usr/bin/env python3
"""
Analiza el formulario web Enketo y extrae estructura completa (campos, grupos, labels)
para comparar con el PDF.
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import FORM_URL, HEADLESS

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_JSON = PROJECT_ROOT / "formulario_web_estructura.json"
OUTPUT_MD = PROJECT_ROOT / "formulario_web_analisis.md"


def analyze_form() -> list[dict]:
    """Extrae campos del formulario con label, type y path."""
    fields = []

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
                const els = document.querySelectorAll('input[name], textarea[name], select[name], [data-name]');
                const seen = new Set();
                const JUNK_NAMES = new Set(['search', 'lat', 'long', 'alt', 'acc']);
                els.forEach(el => {
                    const name = el.getAttribute('name') || el.getAttribute('data-name');
                    if (!name || seen.has(name)) return;
                    if (/^\\d+(\\.\\d+)?$/.test(name)) return;
                    if (name.startsWith('leaflet-')) return;
                    if (JUNK_NAMES.has(name)) return;
                    if (name.startsWith('__') || name === 'undefined') return;
                    seen.add(name);
                    const type = el.type || el.tagName.toLowerCase();
                    let label = '';
                    const labelEl = el.closest('.question')?.querySelector('label, .question-label');
                    if (labelEl) label = labelEl.textContent?.trim().substring(0, 80) || '';
                    const groupEl = el.closest('.or-group, [role="group"]');
                    let group = '';
                    if (groupEl) {
                        const h = groupEl.querySelector('h4, .group-label, legend');
                        if (h) group = h.textContent?.trim().substring(0, 60) || '';
                    }
                    results.push({
                        path: name,
                        type: type,
                        label: label,
                        group: group,
                        short: name.split('/').pop() || name
                    });
                });
                return results;
            }
            """
            raw = page.evaluate(js_extract)
            if isinstance(raw, list):
                fields = raw

        finally:
            browser.close()

    return fields


def group_by_prefix(fields: list[dict]) -> dict:
    """Agrupa campos por el prefijo del path (ej. group_py4vt65)."""
    groups = {}
    for f in fields:
        parts = f["path"].split("/")
        if len(parts) >= 2:
            key = parts[-2]  # group_xxx o meta, formhub
            if key not in groups:
                groups[key] = []
            groups[key].append(f)
        else:
            if "_root" not in groups:
                groups["_root"] = []
            groups["_root"].append(f)
    return groups


def main() -> None:
    print(f"Analizando formulario: {FORM_URL}")
    try:
        fields = analyze_form()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not fields:
        print("No se encontraron campos.")
        sys.exit(1)

    groups = group_by_prefix(fields)

    # Guardar JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"fields": fields, "groups": {k: [x["short"] for x in v] for k, v in groups.items()}}, f, indent=2, ensure_ascii=False)
    print(f"JSON guardado en: {OUTPUT_JSON}")

    # Generar Markdown
    lines = [
        "# Análisis del formulario web KoboToolbox/Enketo",
        "",
        f"URL: {FORM_URL}",
        f"Total campos: {len(fields)}",
        "",
        "## Campos por grupo",
        "",
    ]
    for group_name, group_fields in sorted(groups.items()):
        lines.append(f"### {group_name}")
        lines.append("")
        for f in group_fields:
            lbl = (f.get("label") or "")[:60]
            lines.append(f"- **{f['short']}** ({f.get('type', '')})")
            if lbl:
                lines.append(f"  - Label: {lbl}")
            lines.append(f"  - Path: `{f['path']}`")
            lines.append("")
        lines.append("")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Markdown guardado en: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
