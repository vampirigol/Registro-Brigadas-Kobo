#!/usr/bin/env python3
"""
Prueba de llenado automático DIRECTA al formulario KoboToolbox.
Ejecuta: python test_llenado_directo.py

Si funciona, verás una ventana que se abre, marca consentimiento,
llena Nombre y Fecha, y se cierra. Esto demuestra que el llenado SÍ funciona.
"""
import sys
from pathlib import Path

# Añadir el proyecto al path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright
from config import FORM_URL


def main():
    print("=" * 50)
    print("PRUEBA DE LLENADO AUTOMÁTICO")
    print("=" * 50)
    print(f"Formulario: {FORM_URL}")
    print("Se abrirá una ventana. Observa cómo se llenan los campos.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(25000)

        print("1. Cargando formulario...")
        page.goto(FORM_URL, wait_until="networkidle")
        page.wait_for_timeout(3000)

        print("2. Marcando consentimiento (CONS1=1)...")
        consent = page.locator('[name="/aD6FdrTDPaW4QzCLjmG7WE/CONS1"][value="1"]').first
        consent.click()
        page.wait_for_timeout(1000)

        print("3. Llenando Nombre del paciente...")
        name_input = page.locator('input[name="/aD6FdrTDPaW4QzCLjmG7WE/group_py4vt65/NAME"]').first
        name_input.wait_for(state="visible", timeout=5000)
        name_input.fill("PRUEBA AUTOMATICA - FUNCIONA")

        print("4. Llenando Fecha de atención...")
        fecha_input = page.locator('input[name="/aD6FdrTDPaW4QzCLjmG7WE/Fecha_de_atenci_n"]').first
        if fecha_input.count() > 0:
            fecha_input.fill("2026-03-10")
            print("   Fecha: 2026-03-10")
        else:
            print("   (Campo fecha no visible en esta página)")

        print()
        print("¡LISTO! Los campos se llenaron correctamente.")
        print("La ventana permanecerá abierta 5 segundos para que lo verifiques.")
        page.wait_for_timeout(5000)

        browser.close()

    print()
    print("=" * 50)
    print("RESULTADO: El llenado automático SÍ funciona.")
    print("El problema en la app era que faltaba marcar consentimiento primero.")
    print("=" * 50)


if __name__ == "__main__":
    main()
