"""
Envío de datos a KoboToolbox vía API (XML).
Más preciso que el llenado por navegador: los datos se envían directamente al servidor.

Requisitos: KOBO_API_TOKEN y KOBO_ASSET_UID en .env
Documentación: https://support.kobotoolbox.org/ (REST API)
"""

import io
import logging
import uuid
from datetime import datetime
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)
_OWNER_CACHE: dict[tuple[str, str], str] = {}


def _path_to_tags(path: str, root_id: str) -> list[str]:
    """Convierte path tipo /aD6F.../group/POC en ['group', 'POC']."""
    parts = path.strip("/").split("/")
    if parts and parts[0] == root_id:
        parts = parts[1:]
    return parts


def _resolve_owner_username(api_token: str, asset_uid: str, kc_url: str) -> str:
    """
    Obtiene el owner del formulario desde /api/v1/forms.
    Se usa para enviar a /{owner}/submission (endpoint OpenRosa correcto).
    """
    key = (kc_url.rstrip("/"), asset_uid.strip())
    if key in _OWNER_CACHE:
        return _OWNER_CACHE[key]

    url = f"{kc_url.rstrip('/')}/api/v1/forms"
    r = requests.get(url, headers={"Authorization": f"Token {api_token}"}, timeout=20)
    r.raise_for_status()
    forms = r.json() if "application/json" in (r.headers.get("content-type") or "") else []
    if isinstance(forms, list):
        for form in forms:
            if str(form.get("id_string", "")).strip() == asset_uid.strip():
                owner = str(form.get("owner", "")).strip()
                if owner:
                    _OWNER_CACHE[key] = owner
                    return owner
    raise RuntimeError(f"No se pudo resolver owner para asset_uid={asset_uid}")


def _build_submission_xml(record: dict[str, str], mapping: dict[str, str], asset_uid: str) -> bytes:
    """Construye XML OpenRosa con raíz del formulario (asset_uid)."""
    root_id = asset_uid.strip()
    root = ET.Element(root_id, attrib={"id": root_id})

    formhub = ET.SubElement(root, "formhub")
    ET.SubElement(formhub, "uuid").text = str(uuid.uuid4()).replace("-", "")[:24]
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    ET.SubElement(root, "start").text = now
    ET.SubElement(root, "end").text = now

    parents: dict[str, ET.Element] = {"": root}
    for col, value in record.items():
        path = mapping.get(col)
        value_str = str(value or "").strip()
        if not path or not value_str:
            continue
        tags = _path_to_tags(path, root_id)
        if not tags:
            continue
        parent = root
        for i, tag in enumerate(tags[:-1]):
            key = "/".join(tags[: i + 1])
            if key not in parents:
                parents[key] = ET.SubElement(parent, tag)
            parent = parents[key]
        ET.SubElement(parent, tags[-1]).text = value_str

    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "instanceID").text = f"uuid:{uuid.uuid4()}"

    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue()


def submit_via_api(
    record: dict[str, str],
    mapping: dict[str, str],
    *,
    api_token: str,
    asset_uid: str,
    kc_url: str = "https://kc.kobotoolbox.org",
) -> tuple[bool, str]:
    """
    Envía un registro a KoboToolbox vía API (XML).

    Returns:
        (success, message)
    """
    if not api_token or not asset_uid:
        return False, "Faltan KOBO_API_TOKEN o KOBO_ASSET_UID en .env"

    try:
        owner = _resolve_owner_username(api_token, asset_uid, kc_url)
        xml_bytes = _build_submission_xml(record, mapping, asset_uid)
    except Exception as e:
        logger.exception("Error preparando envío API Kobo")
        return False, f"Error preparando envío: {e}"

    url = f"{kc_url.rstrip('/')}/{owner}/submission"
    headers = {"Authorization": f"Token {api_token}"}
    files = {"xml_submission_file": ("submission.xml", io.BytesIO(xml_bytes), "application/xml")}

    try:
        r = requests.post(url, files=files, headers=headers, timeout=30)
    except requests.RequestException as e:
        logger.warning("Error de red al enviar a Kobo: %s", e)
        return False, f"Error de red: {e}"

    if r.status_code in (200, 201):
        logger.info("Envío API OK (%s)", r.status_code)
        return True, "Enviado correctamente por API"

    try:
        err = r.json()
        detail = err.get("detail", err.get("message", r.text[:200]))
    except Exception:
        detail = r.text[:200] if r.text else f"HTTP {r.status_code}"
    logger.warning("API Kobo error %s: %s", r.status_code, detail)
    return False, f"API {r.status_code}: {detail}"
