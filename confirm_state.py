"""
Estado compartido para que el usuario valide la carga de cada fila
antes de enviar el formulario en KoboToolbox.

Modo threading (mismo proceso): evento + lock.
Modo archivo (KOBO_CONFIRM_FILE): el proceso padre y el hijo comparten un fichero
(p. ej. carga en subprocess bajo Gunicorn).
"""

import os
import threading
import time
from pathlib import Path

_confirm_event = threading.Event()
_confirm_action: str | None = None  # "confirm" | "skip"
_lock = threading.Lock()


def _confirm_file_path() -> str | None:
    p = os.environ.get("KOBO_CONFIRM_FILE", "").strip()
    return p or None


def reset() -> None:
    """Resetea el estado (llamar antes de esperar)."""
    path = _confirm_file_path()
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            pass
        return
    with _lock:
        global _confirm_action
        _confirm_action = None
        _confirm_event.clear()


def _wait_confirm_file(path: str, timeout: int) -> bool:
    """True = confirmar envío, False = omitir o timeout."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if p.exists():
                raw = p.read_text(encoding="utf-8", errors="replace").strip().lower()
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
                if raw == "confirm":
                    return True
                if raw == "skip":
                    return False
        except OSError:
            pass
        time.sleep(0.15)
    return False


def wait_for_confirm(timeout: int = 300) -> bool:
    """
    Bloquea hasta que el usuario confirme u omita.
    Returns True si el usuario confirmó enviar, False si omitió.
    """
    path = _confirm_file_path()
    if path:
        return _wait_confirm_file(path, timeout)
    _confirm_event.clear()
    with _lock:
        global _confirm_action
        _confirm_action = None
    _confirm_event.wait(timeout=timeout)
    with _lock:
        return _confirm_action == "confirm"


def signal_confirm(action: str) -> None:
    """Señaliza que el usuario confirmó (action='confirm') u omitió (action='skip')."""
    path = _confirm_file_path()
    if path:
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(action.strip(), encoding="utf-8")
        except OSError:
            pass
        return
    with _lock:
        global _confirm_action
        _confirm_action = action
    _confirm_event.set()
