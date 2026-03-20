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
from typing import Any
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)


def _path_to_tags(path: str, root_id: str) -> list[str]:
    """Convierte path tipo /aD6FdrTDPaW4QzCLjmG7WE/group_nl0pw33/POC en ['group_nl0pw33', 'POC']."""
    parts = path.strip("/").split("/")
    if parts and parts[0] == root_id:
        parts = parts[1:]
    return parts


def _build_submission_xml(record: dict[str, str], mapping: dict[str, str], asset_uid: str) -> bytes:
    """
    Construye el XML de envío con la estructura que espera KoboToolbox.
    Los paths se convierten en jerarquía de etiquetas bajo el root (asset_uid).
    """
    root_id = asset_uid.strip()
    root = ET.Element(root_id, attrib={"id": root_id, "version": "1"})

    # formhub uuid (requerido en muchos formularios)
    formhub = ET.SubElement(root, "formhub")
    ET.SubElement(formhub, "uuid").text = str(uuid.uuid4()).replace("-", "")[:24]

    # start / end (OpenRosa)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    ET.SubElement(root, "start").text = now
    ET.SubElement(root, "end").text = now

    # Nodos por path: agrupar por prefijo para construir jerarquía
    # path ej: /aD6FdrTDPaW4QzCLjmG7WE/group_nl0pw33/POC -> parent=group_nl0pw33, tag=POC
    parents: dict[str, ET.Element] = {}  # path_prefix -> element
    parents[""] = root

    for col, value in record.items():
        path = mapping.get(col)
        if not path or not str(value).strip():
            continue
        tags = _path_to_tags(path, root_id)
        if not tags:
            continue
        value_str = str(value).strip()
        # Evitar caracteres que rompen XML
        if "<" in value_str or "&" in value_str:
            value_str = value_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        parent = root
        for i, tag in enumerate(tags[:-1]):
            key = "/".join(tags[: i + 1])
            if key not in parents:
                parents[key] = ET.SubElement(parent, tag)
            parent = parents[key]
        last_tag = tags[-1]
        child = ET.SubElement(parent, last_tag)
        child.text = value_str

    # meta / instanceID (evita duplicados)
    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "instanceID").text = f"uuid:{uuid.uuid4()}"

    tree = ET.ElementTree(root)
    buf = io.BytesIO()
    tree.write(
        buf,
        encoding="utf-8",
        xml_declaration=True,
        default_namespace="",
        method="xml",
    )
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
        xml_bytes = _build_submission_xml(record, mapping, asset_uid)
    except Exception as e:
        logger.exception("Error construyendo XML")
        return False, f"Error XML: {e}"

    submission_id = str(uuid.uuid4())
    url = f"{kc_url.rstrip('/')}/api/v1/submissions"
    headers = {"Authorization": f"Token {api_token}"}
    files = {"xml_submission_file": (submission_id, io.BytesIO(xml_bytes), "application/xml")}

    try:
        r = requests.post(url, files=files, headers=headers, timeout=30)
    except requests.RequestException as e:
        logger.warning("Error de red al enviar a Kobo: %s", e)
        return False, f"Error de red: {e}"

    if r.status_code == 201:
        logger.info("Envío API OK (201)")
        return True, "Enviado correctamente por API"

    try:
        err = r.json()
        detail = err.get("detail", err.get("message", r.text[:200]))
    except Exception:
        detail = r.text[:200] if r.text else f"HTTP {r.status_code}"
    logger.warning("API Kobo error %s: %s", r.status_code, detail)
    return False, f"API {r.status_code}: {detail}"
