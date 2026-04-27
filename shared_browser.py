"""
Navegador compartido: se abre UNA vez y se reutiliza para la carga.
Evita abrir una ventana nueva cada vez que el usuario hace Iniciar.
"""

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

_shared_page: "Page | None" = None
_shared_playwright = None
_shared_browser = None
_shared_context = None
_lock = threading.Lock()


def get_shared_page():
    """Obtiene la página compartida si existe."""
    with _lock:
        return _shared_page


def set_shared_page(page, playwright=None, browser=None, context=None):
    """Guarda la página compartida."""
    global _shared_page, _shared_playwright, _shared_browser, _shared_context
    with _lock:
        _shared_page = page
        _shared_playwright = playwright
        _shared_browser = browser
        _shared_context = context


def clear_shared():
    """Limpia la referencia (no cierra el navegador)."""
    global _shared_page
    with _lock:
        _shared_page = None
