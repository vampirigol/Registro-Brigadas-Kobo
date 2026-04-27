#!/usr/bin/env python3
"""
Script de diagnóstico para identificar la estructura del formulario Enketo/KoboToolbox.
Navega a FORM_URL, analiza iframes y campos, y guarda resultado en logs/diagnostico_form.txt

Uso:
  python diagnostic_form.py           # Ejecuta y guarda resultado
  python diagnostic_form.py --pause   # Pausa al final para inspección manual
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import FORM_URL, LOGS_DIR


def run_diagnostic(pause: bool = False) -> None:
    """Ejecuta el diagnóstico del formulario."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LOGS_DIR / "diagnostico_form.txt"
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        lines.append(msg)

    log(f"=== Diagnóstico del formulario KoboToolbox ===")
    log(f"URL: {FORM_URL}")
    log("")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not pause)
        page = browser.new_page()
        page.set_default_timeout(60000)

        try:
            log("1. Navegando a FORM_URL (networkidle)...")
            page.goto(FORM_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(8000)
            log("   Carga completada.")
            log("")

            log("2. Análisis de iframes en la página principal:")
            iframe_count = page.locator("iframe").count()
            log(f"   Total iframes: {iframe_count}")
            for i in range(iframe_count):
                ifr = page.locator("iframe").nth(i)
                src = ifr.get_attribute("src") or "(sin src)"
                id_attr = ifr.get_attribute("id") or "(sin id)"
                log(f"   - iframe[{i}]: id={id_attr}, src={src[:80]}...")
            log("")

            log("3. Frames disponibles (page.frames):")
            frames = page.frames()
            for i, f in enumerate(frames):
                try:
                    url = f.url[:100] if f.url else "(vacío)"
                    log(f"   - Frame {i}: {url}")
                except Exception as e:
                    log(f"   - Frame {i}: (error: {e})")
            log("")

            log("4. Búsqueda de campos en documento principal:")
            cons1_main = page.locator('[name*="CONS1"]').count()
            log(f"   Campos [name*='CONS1'] en main: {cons1_main}")
            fecha_main = page.locator('[name*="Fecha_de_atenci_n"]').count()
            log(f"   Campos [name*='Fecha_de_atenci_n'] en main: {fecha_main}")
            log("")

            log("5. Búsqueda en iframe principal (iframe:first-of-type):")
            try:
                if iframe_count == 0:
                    log("   No hay iframes; saltando.")
                else:
                    frame = page.frame_locator("iframe").first
                    cons1_frame = frame.locator('[name*="CONS1"]').count()
                    log(f"   Campos [name*='CONS1'] en iframe: {cons1_frame}")
                    fecha_frame = frame.locator('[name*="Fecha_de_atenci_n"]').count()
                    log(f"   Campos [name*='Fecha_de_atenci_n'] en iframe: {fecha_frame}")
            except Exception as e:
                log(f"   Error accediendo iframe: {e}")
            log("")

            log("6. Selectores Next/Submit en main:")
            next_main = page.locator('button:has-text("Next"), button:has-text("Siguiente")').count()
            submit_main = page.locator('button:has-text("Submit"), button:has-text("Enviar")').count()
            log(f"   Botones Next/Siguiente: {next_main}")
            log(f"   Botones Submit/Enviar: {submit_main}")

            log("")
            log("7. Selectores Next/Submit en iframe:")
            try:
                if iframe_count > 0:
                    frame = page.frame_locator("iframe").first
                    next_frame = frame.locator('button:has-text("Next"), button:has-text("Siguiente")').count()
                    submit_frame = frame.locator('button:has-text("Submit"), button:has-text("Enviar")').count()
                    log(f"   Botones Next/Siguiente: {next_frame}")
                    log(f"   Botones Submit/Enviar: {submit_frame}")
                else:
                    log("   No hay iframes; saltando.")
            except Exception as e:
                log(f"   Error: {e}")

        except Exception as e:
            log(f"\nERROR: {e}")
            import traceback

            log(traceback.format_exc())
        finally:
            output_path.write_text("\n".join(lines), encoding="utf-8")
            log("")
            log(f"Resultado guardado en: {output_path}")

            if pause:
                input("\nPulsa Enter para cerrar el navegador...")
            browser.close()

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnóstico del formulario KoboToolbox")
    parser.add_argument("--pause", action="store_true", help="Pausa al final para inspección manual")
    args = parser.parse_args()
    run_diagnostic(pause=args.pause)
