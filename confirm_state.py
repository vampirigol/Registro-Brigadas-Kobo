"""
Estado compartido para que el usuario valide la carga de cada fila
antes de enviar el formulario en KoboToolbox.
"""

import threading

_confirm_event = threading.Event()
_confirm_action: str | None = None  # "confirm" | "skip"
_lock = threading.Lock()


def reset() -> None:
    """Resetea el estado (llamar antes de esperar)."""
    with _lock:
        global _confirm_action
        _confirm_action = None
        _confirm_event.clear()


def wait_for_confirm(timeout: int = 300) -> bool:
    """
    Bloquea hasta que el usuario confirme o omita.
    Returns True si el usuario confirmó enviar, False si omitió.
    """
    _confirm_event.clear()
    with _lock:
        global _confirm_action
        _confirm_action = None
    _confirm_event.wait(timeout=timeout)
    with _lock:
        return _confirm_action == "confirm"


def signal_confirm(action: str) -> None:
    """Señaliza que el usuario confirmó (action='confirm') u omitió (action='skip')."""
    with _lock:
        global _confirm_action
        _confirm_action = action
    _confirm_event.set()
