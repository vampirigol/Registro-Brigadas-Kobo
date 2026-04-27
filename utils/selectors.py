"""Construcción de selectores CSS para el formulario Enketo."""


def build_selectors_for_field(field_path: str) -> list[str]:
    """
    Genera una lista de selectores CSS para un campo del formulario Enketo.
    Prioridad: name, luego data-name, luego data-path.

    Args:
        field_path: Path del campo (ej. /data/pregunta1 o /data/grupo/campo)

    Returns:
        Lista de selectores CSS a intentar en orden de prioridad.
    """
    # Enketo puede usar name, data-name; a veces con/sin prefijo
    short_name = field_path.split("/")[-1] if "/" in field_path else field_path
    selectors = [
        f'input[name="{field_path}"]',
        f'textarea[name="{field_path}"]',
        f'select[name="{field_path}"]',
        f'[name="{field_path}"]',
        f'[data-name="{field_path}"]',
        f'[data-path="{field_path}"]',
        f'input[name$="{short_name}"]',
        f'[name$="{short_name}"]',
    ]
    return selectors


def build_radio_selector(field_path: str, value: str) -> list[str]:
    """
    Genera selectores para radio buttons o checkboxes por valor.

    Args:
        field_path: Path del campo
        value: Valor a seleccionar

    Returns:
        Lista de selectores a intentar.
    """
    selectors = [
        f'input[name="{field_path}"][value="{value}"]',
        f'[name="{field_path}"][value="{value}"]',
        f'[data-name="{field_path}"][value="{value}"]',
        f'label:has(input[value="{value}"])',
    ]
    return selectors
