"""Constantes y tipos compartidos para el llenado del formulario Enketo."""

from pathlib import Path
from typing import Union

from playwright.sync_api import FrameLocator, Page

# Contexto del formulario: Page (documento principal) o FrameLocator (iframe)
FormContext = Union[Page, FrameLocator]

# Rutas de Chrome/Chromium en macOS
CHROME_PATHS_MACOS = [
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
]

# Campos que SIEMPRE se rellenan por defecto al inicio usando VALUES REALES del formulario
DEFAULT_FIELDS_ORDER = [
    ("CONS1", "1"),                      # "1" = Sí en el formulario
    ("Modalidad_de_la_atenci_n", "1"),   # "1" = Móvil
    ("POC", "4"),                        # "4" = Otro (se sobreescribe con el valor real del record)
    ("followup", "1"),                   # "1" = Primera vez
    ("ASESPREV", "Medicina General"),
]

# Selector para detectar campos del formulario Enketo en cualquier contexto
_FIELD_SELECTOR = (
    "[name*='CONS1'], [name*='Fecha_de_atenci_n'], [data-name*='CONS1'], [data-name*='Fecha'], "
    "input[type='text'], input[type='date'], input[type='number'], "
    "textarea, select, input[type='radio']"
)

# Si el formulario usa códigos para Estado (POC) en vez de etiqueta, probar ambos.
# Basado en diagnóstico DOM: POC options=[baja_california(Baja California),1(Baja Californa),
#   2(Chihuahua),nuevo_le_n(Nuevo León),3(Sonora),4(Otro)]
POC_ESTADO_ALTERNATIVOS: dict[str, list[str]] = {
    "1":               ["BCS", "baja_californa_sur", "Baja Californa Sur", "Baja California Sur"],
    "2":               ["CHIH", "chihuahua", "Chihuahua"],
    "3":               ["sonora", "Sonora"],
    "baja_california": ["Baja California", "baja california"],
    "nuevo_le_n":      ["Nuevo León", "nuevo_leon", "nuevo_le_n"],
    "4":               ["Otro", "otro"],
}

# Selectores para botones Enketo
SUBMIT_SELECTORS = [
    'button:has-text("Submit")',
    'button:has-text("Enviar")',
    '[type="submit"]',
    '[data-role="submit"]',
    'button[type="submit"]',
    '.btn-submit',
]

NEXT_SELECTORS = [
    'button:has-text("Next")',
    'button:has-text("Siguiente")',
    '[data-role="next"]',
    '.btn-next',
    'a:has-text("Next")',
    'button.next',
    '[type="button"]:has-text("Siguiente")',
]
