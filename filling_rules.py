"""
Reglas de llenado del formulario KoboToolbox según instrucciones del usuario.
Aplica valores por defecto y transformaciones antes de enviar al form_filler.

VALORES REALES DEL FORMULARIO (obtenidos por diagnóstico del DOM):
  CONS1:        "1"=Sí, "0"=No
  Modalidad:    "1"=Móvil, "albergues", "centros_comunitarios", "2"=Clínica Adventista, "escuelas"
  POC (Estado): "baja_california", "1"=Baja Californa Sur, "2"=Chihuahua,
                "nuevo_le_n"=Nuevo León, "3"=Sonora, "4"=Otro
  followup:     "1"=Primera vez, "2"=Seguimiento, "3"=Atención Única, "4"=Entrega de Insumos
"""

import re
import unicodedata
from datetime import date
from typing import Callable
import logging

from coords_store import (
    coords_to_string,
    get_coords_for_lugar,
    parse_coords_string,
    upsert_coords_for_lugar,
)

logger = logging.getLogger(__name__)

# ── Geocodificación con Nominatim (OpenStreetMap) ─────────────────────────────
# Caché en memoria para no repetir llamadas al mismo lugar durante la sesión
_geo_cache: dict[str, str] = {}

# Coordenadas de respaldo para los lugares conocidos del programa
# Formato KoboToolbox: "latitud longitud altitud precision"
_GEO_FALLBACK: dict[str, str] = {
    "santa rosalia":          "27.3376 -112.2707 0 0",
    "santa rosalía":          "27.3376 -112.2707 0 0",
    "mulege":                 "26.8884 -111.9814 0 0",
    "mulegé":                 "26.8884 -111.9814 0 0",
    "loreto":                 "26.0115 -111.3414 0 0",
    "ciudad constitucion":    "25.0389 -111.6707 0 0",
    "ciudad constitución":    "25.0389 -111.6707 0 0",
    "vizcaino":               "27.600992342277443 -113.57458248245227 0 0",
    "vizcaíno":               "27.600992342277443 -113.57458248245227 0 0",
    "bahia tortuga":          "27.6765 -114.9015 0 0",
    "bahía tortuga":          "27.6765 -114.9015 0 0",
    "bahia asuncion":         "27.1290 -114.2890 0 0",
    "bahía asunción":         "27.1290 -114.2890 0 0",
    "punta abreojos":         "26.7164 -113.5575 0 0",
    "la bucana":              "25.8500 -111.0500 0 0",
    "valle de la trinidad":   "31.3612 -115.7933 0 0",
    "san matias":             "31.5180 -115.2820 0 0",
    "san matías":             "31.5180 -115.2820 0 0",
    "santa catalina":         "30.0000 -115.8000 0 0",
    "comunidad kiliwa":       "31.1833 -115.6167 0 0",
    "kiliwa":                 "31.1833 -115.6167 0 0",
    "tijuana":                "32.5149 -117.0382 0 0",
    "ciudad juarez":          "31.6904 -106.4245 0 0",
    "ciudad juárez":          "31.6904 -106.4245 0 0",
    "montemorelos":           "25.1912 -99.8291 0 0",
    "ciudad obregon":         "27.4863 -109.9307 0 0",
    "ciudad obregón":         "27.4863 -109.9307 0 0",
}


def _geocodificar(lugar: str) -> str:
    """
    Convierte un nombre de lugar a coordenadas en formato KoboToolbox
    ("latitud longitud altitud precision") usando Nominatim (OpenStreetMap).

    Estrategia:
    1. Revisar caché en memoria.
    2. Revisar diccionario de respaldo (_GEO_FALLBACK) con normalización.
    3. Llamar a la API de Nominatim con timeout de 5 s.
    4. Si todo falla, retornar cadena vacía.
    """
    if not lugar:
        return ""

    lugar_norm = _norm_str(lugar)

    # 1. Caché
    if lugar_norm in _geo_cache:
        return _geo_cache[lugar_norm]

    # 2. Diccionario de respaldo
    for key, coords in _GEO_FALLBACK.items():
        key_norm = _norm_str(key)
        if lugar_norm == key_norm or key_norm in lugar_norm or lugar_norm in key_norm:
            _geo_cache[lugar_norm] = coords
            logger.info("[GEO] Fallback para '%s' → %s", lugar, coords)
            return coords

    # 3. API de Nominatim
    try:
        import urllib.request
        import urllib.parse
        import json as _json

        query = f"{lugar}, México"
        params = urllib.parse.urlencode({"q": query, "format": "json", "limit": "1"})
        url = f"https://nominatim.openstreetmap.org/search?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "KoboLlenado/1.0 (brigadas-salud)"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode("utf-8"))

        if data:
            lat = data[0]["lat"]
            lon = data[0]["lon"]
            coords = f"{lat} {lon} 0 0"
            _geo_cache[lugar_norm] = coords
            logger.info("[GEO] Nominatim '%s' → %s", lugar, coords)
            return coords
        else:
            logger.warning("[GEO] Nominatim sin resultados para '%s'", lugar)

    except Exception as exc:
        logger.warning("[GEO] Error geocodificando '%s': %s", lugar, exc)

    _geo_cache[lugar_norm] = ""
    return ""

# ── Mapeo de texto del Excel → VALUE real del formulario (campo POC) ──────────
ESTADO_TO_FORM_VALUE = {
    "baja california sur":  "1",              # "Baja Californa Sur" en el form (typo)
    "baja californa sur":   "1",
    "bcs":                  "1",
    "chihuahua":            "2",
    "sonora":               "3",
    "baja california":      "baja_california",
    "nuevo león":           "nuevo_le_n",
    "nuevo leon":           "nuevo_le_n",
}
# Value del campo POC para la opción "Otro"
POC_OTRO = "4"

# ── Mapeo Estado (POC value) → campo de Lugar de Atención + opciones válidas ──
# Los valores de la lista son las etiquetas exactas del formulario.
# "Otro" NO se incluye aquí; se maneja automáticamente si no hay coincidencia.
LUGAR_POR_ESTADO: dict[str, dict] = {
    "1": {  # Baja California Sur
        "field": "BCS",
        "lugares": [
            "Santa Rosalía",
            "Mulege",
            "Loreto",
            "Ciudad Constitución",
            "Vizcaíno",
            "Bahía Tortuga",
            "Bahía Asunción",
            "Punta Abreojos",
            "La Bucana",
        ],
    },
    "baja_california": {  # Baja California
        "field": "Lugar_de_Atenci_n_Baja_Califo",
        "lugares": [
            "Valle de la Trinidad",
            "San Matías",
            "Santa Catalina",
            "Comunidad Kiliwa",
            "Tijuana",
        ],
    },
    "2": {  # Chihuahua
        "field": "CHIH",
        "lugares": [
            "Ciudad Juárez",
        ],
    },
    "nuevo_le_n": {  # Nuevo León
        "field": "Lugar_de_Atenci_n_Nuevo_Le_n",
        "lugares": [
            "Montemorelos",
        ],
    },
    "3": {  # Sonora
        "field": "Lugar_de_Atenci_n_Sonora",
        "lugares": [
            "Ciudad Obregón",
        ],
    },
}

# Etiqueta legible (para el campo Estado del paciente, que también es radio)
ESTADO_LABEL_FROM_VALUE = {
    "1":               "Baja Californa Sur",
    "2":               "Chihuahua",
    "3":               "Sonora",
    "baja_california": "Baja California",
    "nuevo_le_n":      "Nuevo León",
    "4":               "Otro",
}

# Motivos de referencia
MOTIVO_REFERENCIA = {
    "desnutrición":              "Desnutrición",
    "desnutricion":              "Desnutrición",
    "seguimiento embarazo":      "Seguimiento embarazo",
    "valoración y tratamiento":  "Valoración y tratamiento",
    "valoracion y tratamiento":  "Valoración y tratamiento",
    "pb neumonía":               "PB Neumonía",
    "neumonia":                  "PB Neumonía",
    "cirugía":                   "Cirugía",
    "cirugia":                   "Cirugía",
}


# ── Mapeo de texto del Excel → etiqueta exacta del formulario (campo Estado del paciente) ──
# El formulario usa los nombres oficiales de los estados de México.
ESTADO_PACIENTE_ALIAS: dict[str, str] = {
    "aguascalientes":          "Aguascalientes",
    "baja california":         "Baja California",
    "baja california norte":   "Baja California",
    "bc":                      "Baja California",
    "baja california sur":     "Baja California Sur",
    "bcs":                     "Baja California Sur",
    "campeche":                "Campeche",
    "chiapas":                 "Chiapas",
    "chihuahua":               "Chihuahua",
    "chih":                    "Chihuahua",
    "ciudad de mexico":        "Ciudad de México",
    "ciudad de méxico":        "Ciudad de México",
    "cdmx":                    "Ciudad de México",
    "df":                      "Ciudad de México",
    "distrito federal":        "Ciudad de México",
    "coahuila":                "Coahuila",
    "coahuila de zaragoza":    "Coahuila",
    "colima":                  "Colima",
    "durango":                 "Durango",
    "estado de mexico":        "Estado de México",
    "estado de méxico":        "Estado de México",
    "edomex":                  "Estado de México",
    "mexico":                  "Estado de México",
    "méxico":                  "Estado de México",
    "guanajuato":              "Guanajuato",
    "guerrero":                "Guerrero",
    "hidalgo":                 "Hidalgo",
    "jalisco":                 "Jalisco",
    "michoacan":               "Michoacán",
    "michoacán":               "Michoacán",
    "morelos":                 "Morelos",
    "nayarit":                 "Nayarit",
    "nuevo leon":              "Nuevo León",
    "nuevo león":              "Nuevo León",
    "nl":                      "Nuevo León",
    "oaxaca":                  "Oaxaca",
    "puebla":                  "Puebla",
    "queretaro":               "Querétaro",
    "querétaro":               "Querétaro",
    "quintana roo":            "Quintana Roo",
    "san luis potosi":         "San Luis Potosí",
    "san luis potosí":         "San Luis Potosí",
    "slp":                     "San Luis Potosí",
    "sinaloa":                 "Sinaloa",
    "sonora":                  "Sonora",
    "son":                     "Sonora",
    "tabasco":                 "Tabasco",
    "tamaulipas":              "Tamaulipas",
    "tlaxcala":                "Tlaxcala",
    "veracruz":                "Veracruz",
    "veracruz de ignacio de la llave": "Veracruz",
    "yucatan":                 "Yucatán",
    "yucatán":                 "Yucatán",
    "zacatecas":               "Zacatecas",
    # Extranjero
    "extranjero":              "Extranjero",
    "exterior":                "Extranjero",
    "estados unidos":          "Extranjero",
    "ee.uu.":                  "Extranjero",
    "eeuu":                    "Extranjero",
    "usa":                     "Extranjero",
    "honduras":                "Extranjero",
    "guatemala":               "Extranjero",
    "el salvador":             "Extranjero",
    "nicaragua":               "Extranjero",
    "venezuela":               "Extranjero",
    "cuba":                    "Extranjero",
    "haiti":                   "Extranjero",
    "haití":                   "Extranjero",
}


# Separador para campos select-multiple en el payload
MULTISELECT_SEP = "|||"

# ── Diagnósticos de Medicina General (etiquetas exactas del formulario) ────────
DX_OPTIONS = [
    "Consulta de rutina",
    "Diarrea aguda",
    "Dermatosis",
    "Bronquitis aguda",
    "Embarazo",
    "Parasitosis",
    "Dolor abdominal",
    "Amigdalitis",
    "Desnutrición",
    "Anemia",
    "Síndrome febril",
    "Asma",
    "Cefalea",
    "Pediculosis",
    "Deshidratación",
    "Rinofaringitis",
    "Rinitis alérgica",
    "Conjuntivitis",
    "Escabiosis",
    "Dermatitis alérgica",
    "Estreñimiento",
    "Amenorrea",
    "Carie dental",
    "Cistitis",
    "Consulta de seguimiento",
    "Dermatitis irritante primaria del pañal",
    "Faringoamigdalitis aguda",
    "Gastroenteritis o colitis de origen infeccioso (sin especificación del agente infeccioso)",
    "Herida",
    "Otitis media",
    "Pielonefritis aguda",
    "Quemadura",
    "Sospecha de dengue (Con signos de alarma)",
    "Sospecha de dengue (Sin signos de alarma)",
    "Sospecha de neumonía",
    "Sospecha de rubeola",
    "Sospecha de sarampión",
    "Sospecha de malaria",
    "Traumatismos",
    "Vaginitis",
    "Vaginosis",
    "Varicela",
    "Otro",
]

# ── Diagnósticos de Odontología (etiquetas exactas del formulario) ────────────
DX_DENTAL_OPTIONS = [
    "Caries",
    "Cálculo",
    "Sarro",
    "Gingivitis",
    "Periodontitis",
    "Pulpitis Reversible",
    "Pulpitis Irreversible",
    "Fractura",
    "Otro",
]

# Alias textuales del Excel → opción dental exacta del formulario
_DX_DENTAL_ALIASES: dict[str, str] = {
    "carie":                  "Caries",
    "caries":                 "Caries",
    "carie dental":           "Caries",
    "calculo":                "Cálculo",
    "cálculo":                "Cálculo",
    "calculo dental":         "Cálculo",
    "tartaro":                "Cálculo",
    "tártaro":                "Cálculo",
    "sarro":                  "Sarro",
    "sarro dental":           "Sarro",
    "gingivitis":             "Gingivitis",
    "periodontitis":          "Periodontitis",
    "enfermedad periodontal": "Periodontitis",
    "pulpitis reversible":    "Pulpitis Reversible",
    "pulpitis rev":           "Pulpitis Reversible",
    "pulpitis irreversible":  "Pulpitis Irreversible",
    "pulpitis irrev":         "Pulpitis Irreversible",
    "pulpitis":               "Pulpitis Reversible",
    "fractura":               "Fractura",
    "fractura dental":        "Fractura",
    "diente fracturado":      "Fractura",
    "otro":                   "Otro",
    "otros":                  "Otro",
}


def _map_diagnostico_dental(text: str) -> tuple[str, str]:
    """
    Interpreta el texto de Diagnostico_Motivo del Excel contra los diagnósticos
    de Odontología (Diagn_stico_001).
    Retorna (dx_value, especificar):
      dx_value    → etiquetas coincidentes separadas por ||| para el formulario
      especificar → texto libre cuando algún diagnóstico cae en "Otro"
    """
    text = str(text or "").strip()
    if not text:
        return "", ""

    dx_norm = {_norm_str(opt): opt for opt in DX_DENTAL_OPTIONS if opt != "Otro"}
    alias_norm = {_norm_str(k): v for k, v in _DX_DENTAL_ALIASES.items()}

    matched: list[str] = []
    unmatched: list[str] = []

    parts = [p.strip() for p in re.split(r"[,;\n/]+", text) if p.strip()]
    if not parts:
        parts = [text]

    for part in parts:
        norm_part = _norm_str(part)
        found_opt: str | None = None

        # 1. Alias exacto
        if norm_part in alias_norm:
            found_opt = alias_norm[norm_part]

        # 2. Opción exacta normalizada
        if found_opt is None and norm_part in dx_norm:
            found_opt = dx_norm[norm_part]

        # 3. Coincidencia parcial (el texto contiene o está contenido en la opción)
        if found_opt is None:
            for norm_opt, original_opt in dx_norm.items():
                if norm_part and len(norm_part) > 3 and norm_part in norm_opt:
                    found_opt = original_opt
                    break
                if norm_opt and len(norm_opt) > 3 and norm_opt in norm_part:
                    found_opt = original_opt
                    break

        # 4. Alias parcial
        if found_opt is None:
            for norm_alias, mapped_opt in alias_norm.items():
                if norm_alias and len(norm_alias) > 3 and norm_alias in norm_part:
                    found_opt = mapped_opt
                    break

        if found_opt:
            if found_opt not in matched:
                matched.append(found_opt)
        else:
            unmatched.append(part)

    especificar = ""
    if unmatched:
        if "Otro" not in matched:
            matched.append("Otro")
        especificar = ", ".join(unmatched)

    if not matched:
        matched = ["Otro"]
        especificar = text

    return MULTISELECT_SEP.join(matched), especificar


# ── Procedimientos odontológicos (etiquetas exactas del formulario) ───────────
PROC_DENTAL_OPTIONS = [
    "Resina",
    "Limpieza dental",
    "Endodoncia",
    "Extracción",
    "Cirugía",
    "Otro",
]

_PROC_DENTAL_ALIASES: dict[str, str] = {
    "resina":                   "Resina",
    "restauracion":             "Resina",
    "restauración":             "Resina",
    "obturacion":               "Resina",
    "obturación":               "Resina",
    "empaste":                  "Resina",
    "composite":                "Resina",
    "limpieza":                 "Limpieza dental",
    "limpieza dental":          "Limpieza dental",
    "profilaxis":               "Limpieza dental",
    "detartraje":               "Limpieza dental",
    "tartrectomia":             "Limpieza dental",
    "tartrectomía":             "Limpieza dental",
    "endodoncia":               "Endodoncia",
    "tratamiento de conducto":  "Endodoncia",
    "conducto":                 "Endodoncia",
    "extraccion":               "Extracción",
    "extracción":               "Extracción",
    "exodoncia":                "Extracción",
    "cirugia":                  "Cirugía",
    "cirugía":                  "Cirugía",
    "cirugia dental":           "Cirugía",
    "cirugía dental":           "Cirugía",
    "otro":                     "Otro",
    "otros":                    "Otro",
}


def _map_procedimiento_dental(text: str) -> tuple[str, str]:
    """
    Mapea el texto de la columna 'Procedimiento_dental' del Excel a las opciones
    del formulario (_Qupe_procedimiento_se_realiza).
    Retorna (proc_value, especificar_003):
      proc_value      → opciones separadas por ||| para el checkbox
      especificar_003 → texto libre cuando cae en "Otro"
    """
    text = str(text or "").strip()
    if not text:
        return "", ""

    alias_norm = {_norm_str(k): v for k, v in _PROC_DENTAL_ALIASES.items()}
    opts_norm  = {_norm_str(o): o for o in PROC_DENTAL_OPTIONS if o != "Otro"}

    matched: list[str] = []
    unmatched: list[str] = []

    parts = [p.strip() for p in re.split(r"[,;\n/]+", text) if p.strip()]
    if not parts:
        parts = [text]

    for part in parts:
        norm = _norm_str(part)
        found: str | None = alias_norm.get(norm) or opts_norm.get(norm)

        if not found:
            for k, v in alias_norm.items():
                if k and len(k) > 3 and k in norm:
                    found = v
                    break

        if not found:
            for norm_opt, original_opt in opts_norm.items():
                if norm_opt and len(norm_opt) > 3 and norm_opt in norm:
                    found = original_opt
                    break

        if found:
            if found not in matched:
                matched.append(found)
        else:
            unmatched.append(part)

    especificar = ""
    if unmatched:
        if "Otro" not in matched:
            matched.append("Otro")
        especificar = ", ".join(unmatched)

    if not matched:
        matched = ["Otro"]
        especificar = text

    return MULTISELECT_SEP.join(matched), especificar


# Mapa de variaciones textuales → valor DIS exacto del formulario
DIS_VALUE_ALIASES: dict[str, str] = {
    "motriz":       "motriz",
    "motor":        "motriz",
    "motora":       "motriz",
    "fisica":       "motriz",
    "física":       "motriz",
    "visual":       "visual",
    "vision":       "visual",
    "visión":       "visual",
    "ceguera":      "visual",
    "ciego":        "visual",
    "ciega":        "visual",
    "auditiva":     "auditiva",
    "auditivo":     "auditiva",
    "sordo":        "auditiva",
    "sorda":        "auditiva",
    "sordera":      "auditiva",
    "hipoacusia":   "auditiva",
    "intelectual":  "intelectual",
    "cognitiva":    "intelectual",
    "cognitivo":    "intelectual",
    "mental":       "intelectual",
    "down":         "intelectual",
    "otra":         "otra",
    "otro":         "otra",
    "other":        "otra",
}

# Orden fijo: subcolumnas 0/1 (export Kobo) → clave en registro → etiqueta en DIS
_DIS_FLAG_ORDER: list[tuple[str, str]] = [
    ("DIS_motriz", "Motriz"),
    ("DIS_visual", "Visual"),
    ("DIS_auditiva", "Auditiva"),
    ("DIS_intelectual", "Intelectual"),
    ("DIS_otra", "Otra"),
]
DIS_INTERNAL_TO_KOBO_LABEL: dict[str, str] = {
    "motriz": "Motriz",
    "visual": "Visual",
    "auditiva": "Auditiva",
    "intelectual": "Intelectual",
    "otra": "Otra",
}


def _norm_str(s: str) -> str:
    """Minúsculas y sin tildes para comparaciones robustas."""
    s = str(s or "").lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _is_dis_absent_or_placeholder(text: str) -> bool:
    """N/D, sin dato, etc. → no marcar discapacidades por texto; usar flags si existen."""
    t = _norm_str(text)
    if not t:
        return True
    return t in {
        "n/d",
        "nd",
        "n d",
        "na",
        "n a",
        "no aplica",
        "noaplica",
        "ninguno",
        "ninguna",
        "ningun",
        "ningunna",
        "sin dato",
        "s d",
        "s/d",
        "-",
        "no indicado",
        "no disponible",
    }


def _cell_affirmative_dis(v: object) -> bool:
    s = str(v or "").strip().lower()
    return s in ("1", "sí", "si", "yes", "y", "true", "x", "s")


def _has_dis_flag_column_data(record: dict) -> bool:
    for k, _ in _DIS_FLAG_ORDER:
        if k in record and str(record.get(k, "")).strip() != "":
            return True
    return False


def _dis_from_binary_flags(record: dict) -> tuple[str, str]:
    """
    A partir de DIS_motriz … DIS_otra (0/1 o Sí/No) arma DIS y texto para «Otra».
    """
    labels: list[str] = []
    otra_on = False
    for k, label in _DIS_FLAG_ORDER:
        if k not in record:
            continue
        v = record.get(k)
        if not str(v or "").strip():
            continue
        if not _cell_affirmative_dis(v):
            continue
        labels.append(label)
        if k == "DIS_otra":
            otra_on = True
    dis_val = MULTISELECT_SEP.join(labels) if labels else ""
    dis_esp = ""
    if otra_on:
        dis_esp = str(record.get("Especificar_discapacidad", "")).strip()
        if not dis_esp:
            dis_esp = str(record.get("Discapacidad", "")).strip()
    return dis_val, dis_esp


def _dis_internals_to_kobo_labels(internals_joined: str) -> str:
    if not str(internals_joined or "").strip():
        return ""
    parts = [p.strip() for p in str(internals_joined).split(MULTISELECT_SEP) if p.strip()]
    out_labs: list[str] = []
    for p in parts:
        low = p.lower()
        out_labs.append(DIS_INTERNAL_TO_KOBO_LABEL.get(low, p))
    return MULTISELECT_SEP.join(out_labs)


# Diagnóstico fisioterapia: API Kobo 0/1 (columnas Diagnóstico/… o texto libre)
FISIO_BIN_KEYS: tuple[str, ...] = (
    "FISIO_Revision",
    "FISIO_Artrosis",
    "FISIO_Artritis",
    "FISIO_Lesiones_musculoesqueleticas",
    "FISIO_Dolor_cronico",
    "FISIO_Enf_neurologicas",
    "FISIO_Problemas_respiratorios",
    "FISIO_Dolor",
    "FISIO_Contractura",
    "FISIO_Otro",
)


def _fisio_cell_to_01(v: object) -> str:
    t = str(v or "").strip().lower()
    if t in ("1", "sí", "si", "yes", "y", "true", "x", "s"):
        return "1"
    return "0"


def _fisio_flags_from_text(dx_text: str) -> set[str]:
    """
    A partir de texto (diagnóstico Fisioterapia) detecta qué FISIO_* marcan 1.
    Dolor crónico excluye al mismo tiempo FISIO_Dolor (dolor aislado).
    """
    t = _norm_str(dx_text)
    if not t or t in ("n/d", "nd", "na", "no aplica", "-", "s/d", "s d"):
        return set()
    f: set[str] = set()
    if "revis" in t and "revisor" not in t:
        f.add("FISIO_Revision")
    if "artrosis" in t:
        f.add("FISIO_Artrosis")
    if "artrit" in t:
        f.add("FISIO_Artritis")
    if ("musc" in t and "esq" in t) or "lme" in t or "musculoes" in t:
        f.add("FISIO_Lesiones_musculoesqueleticas")
    dolor_cronico = "dolor" in t and ("cronic" in t or "crono" in t)
    if dolor_cronico:
        f.add("FISIO_Dolor_cronico")
    elif "dolor" in t:
        f.add("FISIO_Dolor")
    if "neurol" in t:
        f.add("FISIO_Enf_neurologicas")
    if "respirat" in t or ("respir" in t and "dific" in t):
        f.add("FISIO_Problemas_respiratorios")
    if "contract" in t:
        f.add("FISIO_Contractura")
    if "otro" in t or t.strip().startswith("otro"):
        f.add("FISIO_Otro")
    return f


def _map_modalidad_excel_to_kobo(record: dict[str, str]) -> str:
    """
    Valor real de Enketo para Modalidad_de_la_atenci_n a partir de Excel/record.
    Valores: "1"=Móvil, "albergues", "centros_comunitarios", "2"=Clínica, "escuelas".
    """
    raw = _pick_first(
        record,
        ["Modalidad_de_la_atenci_n", "Modalidad"],
    )
    s = str(raw or "").strip()
    if not s:
        return "1"
    s_low = s.lower().strip()
    if s_low in ("1", "albergues", "centros_comunitarios", "2", "escuelas"):
        return s_low
    n = _norm_str(s)
    if "alberg" in n:
        return "albergues"
    if "comunit" in n or n.startswith("centro"):
        return "centros_comunitarios"
    if "clinica" in n or "adventista" in n:
        return "2"
    if "escuela" in n:
        return "escuelas"
    if "movil" in n or n == "fija" or s_low in ("movil", "móvil", "fija", "fijo"):
        return "1"
    return "1"


def _map_lugar_atencion(poc_value: str, lugar: str) -> tuple[str, str, bool]:
    """
    Dado el value del campo POC (Estado) y el texto del Lugar de Atención del Excel,
    retorna (field_name, value_to_set, is_otro) donde:
      - field_name  : nombre del campo de radio condicional para ese estado
      - value_to_set: etiqueta del lugar que coincide, o "Otro" si no hay coincidencia
      - is_otro     : True → no se encontró coincidencia; llenar OTH/PLACE; SCH solo si modalidad=Escuelas
    Si poc_value no está en LUGAR_POR_ESTADO (ej. POC_OTRO) retorna ("", "", False).
    """
    config = LUGAR_POR_ESTADO.get(poc_value)
    if not config:
        return "", "", False

    field_name = config["field"]
    lugares_validos: list[str] = config["lugares"]
    lugar_norm = _norm_str(lugar)

    if not lugar_norm:
        return field_name, "Otro", True

    for lugar_opt in lugares_validos:
        opt_norm = _norm_str(lugar_opt)
        if lugar_norm == opt_norm or lugar_norm in opt_norm or opt_norm in lugar_norm:
            return field_name, lugar_opt, False

    return field_name, "Otro", True


def _map_discapacidades(text: str) -> tuple[str, str]:
    """
    Interpreta el texto de la columna Discapacidad del Excel.
    Retorna (dis_value, especificar_discapacidad):
      dis_value  → valores DIS separados por ||| para el formulario
      especificar → texto libre si no coincide con ninguna opción conocida
    Si text está vacío → ("", "") → no marcar nada en el formulario.
    """
    text = str(text or "").strip()
    if not text:
        return "", ""
    if _is_dis_absent_or_placeholder(text):
        return "", ""

    matched: list[str] = []
    unrecognized: list[str] = []

    # Dividir por comas, punto y coma o slash
    parts = [p.strip() for p in re.split(r"[,;/]+", text) if p.strip()]
    if not parts:
        parts = [text]

    for part in parts:
        if _is_dis_absent_or_placeholder(part):
            continue
        norm_part = _norm_str(part)
        found_val = None
        for keyword, dis_val in DIS_VALUE_ALIASES.items():
            if _norm_str(keyword) in norm_part or norm_part in _norm_str(keyword):
                found_val = dis_val
                break
        if found_val and found_val not in matched:
            matched.append(found_val)
        elif not found_val:
            unrecognized.append(part)

    if not matched and not unrecognized:
        return "", ""

    # Si hay partes no reconocidas → marcar "otra" y llenar especificar
    especificar = ""
    if unrecognized:
        if "otra" not in matched:
            matched.append("otra")
        especificar = ", ".join(unrecognized)

    # Si no se reconoció nada → usar "otra" con texto completo
    if not matched:
        matched = ["otra"]
        especificar = text

    return MULTISELECT_SEP.join(matched), especificar


def _map_diagnosticos(text: str) -> tuple[str, str]:
    """
    Interpreta el texto de Diagnostico_Motivo del Excel contra la lista DX del formulario.
    Retorna (dx_value, dxesp):
      dx_value → etiquetas coincidentes separadas por ||| para el formulario
      dxesp    → texto libre si hay diagnósticos que no están en la lista → activa "Otro"
    Si text está vacío → ("", "").
    """
    text = str(text or "").strip()
    if not text:
        return "", ""

    # Pre-calcular versiones normalizadas de las opciones (sin "Otro")
    dx_norm = {_norm_str(opt): opt for opt in DX_OPTIONS if opt != "Otro"}

    matched: list[str] = []
    unmatched: list[str] = []

    # Dividir el texto de entrada por comas, punto y coma, slash o saltos de línea
    parts = [p.strip() for p in re.split(r"[,;\n/]+", text) if p.strip()]
    if not parts:
        parts = [text]

    for part in parts:
        norm_part = _norm_str(part)
        found = False
        # Búsqueda: el texto del Excel contiene a la opción O la opción contiene al texto
        for norm_opt, original_opt in dx_norm.items():
            if norm_part == norm_opt:
                found = True
            elif norm_part and len(norm_part) > 3 and norm_part in norm_opt:
                found = True
            elif norm_opt and len(norm_opt) > 3 and norm_opt in norm_part:
                found = True
            if found:
                if original_opt not in matched:
                    matched.append(original_opt)
                break
        if not found:
            unmatched.append(part)

    dxesp = ""
    if unmatched:
        if "Otro" not in matched:
            matched.append("Otro")
        dxesp = ", ".join(unmatched)

    # Si no coincide nada → todo como "Otro"
    if not matched:
        matched = ["Otro"]
        dxesp = text

    return MULTISELECT_SEP.join(matched), dxesp


def apply_rules(
    record: dict[str, str],
    on_missing: Callable[[str, str], str] | None = None,
) -> dict[str, str]:
    """
    Aplica las reglas de llenado y retorna un record enriquecido con los VALUES
    reales del formulario Enketo (no con etiquetas).
    """
    out: dict[str, str] = {}

    # ── VALORES FIJOS ────────────────────────────────────────────────────────
    # CONS1: Toma de consentimiento → SIEMPRE "Sí" (value="1")
    out["CONS1"] = "1"
    # CONS: Consentimiento verbal al final → SIEMPRE "Sí"
    # Se envía "Sí" (etiqueta visible) para que el JS haga coincidencia por texto del span.
    # Si el formulario usa value="1", el fallback de _fill_field_in_frame lo cubre también.
    out["CONS"] = "Sí"
    out["Modalidad_de_la_atenci_n"] = _map_modalidad_excel_to_kobo(record)
    # Nacionalidad: México por defecto. NATOT (texto bajo el mismo bloque) solo si aplica; no
    # duplicar "México" en NAT y en NATOT salvo que venga en el registro o sea necesario.
    _nat = str(record.get("NAT", "")).strip()
    out["NAT"] = _nat or "México"
    _natot = str(record.get("NATOT", "")).strip()
    if _natot:
        out["NATOT"] = _natot
    # Minoría étnica: No por defecto (value="0"). Si viene la especificación
    # con texto, Kobo requiere que el radio quede marcado como "Sí".
    minoria_raw = str(record.get("_Pertenece_a_alguna_minor_a_t", "")).strip()
    minoria_especifica = str(record.get("Especificar_Minor_a_tnica", "")).strip()
    minoria = _parse_si_no(minoria_raw)
    if not minoria and minoria_raw and minoria_raw.lower() not in ("no", "n", "0", ""):
        minoria = "1"
    if minoria_especifica:
        minoria = "1"
    out["_Pertenece_a_alguna_minor_a_t"] = "1" if minoria == "1" else "0"
    out["Especificar_Minor_a_tnica"] = minoria_especifica if minoria == "1" else ""

    # ── SERVICIO Y ASESORÍA PREVIA ────────────────────────────────────────────
    # Lógica: el "Servicio que se brinda" depende de las especialidades marcadas
    # en el formulario físico (hoja de servicio). Si hay columnas de especialidad
    # presentes en el Excel, se usan para detección automática. Si no, se usa la
    # columna explícita "Servicio que se brinda".
    #
    # ASESPREV (¿Se le ha brindado asesoría en otros módulos hoy?) = los OTROS
    # módulos que el paciente visitó ese día ANTES de la consulta actual.
    # NO debe ser igual al servicio actual (error lógico del fallback anterior).

    # Columnas de especialidad del formulario físico → servicio KoboToolbox
    _ESP_COLS = [
        ("esp_medicina_general", "Medicina General"),
        ("esp_odontologia",      "Dental"),
        ("esp_fisioterapia",     "Fisioterapia"),
        ("esp_oftalmologia",     "Oftalmología"),
        ("esp_laboratorio",      "Laboratorios"),
    ]

    especialidades_marcadas = [
        svc for col, svc in _ESP_COLS
        if _especialidad_marcada(record.get(col, ""))
    ]

    if especialidades_marcadas:
        # Hay columnas de especialidad con datos → determinar servicio automáticamente
        explicit_svc = _norm_servicio(record.get("Servicio_que_se_brinda", ""))
        if explicit_svc and explicit_svc in especialidades_marcadas:
            # El servicio explícito coincide con uno marcado → es el servicio actual
            servicio_actual = explicit_svc
        elif explicit_svc and explicit_svc in SERVICIOS_CANONICOS:
            # La columna "Servicio que se brinda" gana aunque esp_* no coincida (p. ej. padecimiento
            # en otro módulo rellenó solo esp_oftalmologia pero la fila es de Fisioterapia).
            servicio_actual = explicit_svc
        else:
            # Tomar la primera especialidad marcada como servicio actual
            servicio_actual = especialidades_marcadas[0]

        out["Servicio_que_se_brinda"] = servicio_actual

        # ASESPREV = otras especialidades marcadas (visitadas antes de esta consulta)
        otros_modulos = [s for s in especialidades_marcadas if s != servicio_actual]
        if otros_modulos:
            out["ASESPREV"] = MULTISELECT_SEP.join(otros_modulos)
        # Si solo hay un módulo marcado (el actual), ASESPREV queda vacío (sin asesoría previa)

    else:
        # Sin columnas de especialidad → usar columnas explícitas
        out["Servicio_que_se_brinda"] = _norm_servicio(record.get("Servicio_que_se_brinda", ""))

        # ASESPREV: SOLO desde columna explícita del Excel.
        # NO se copia del servicio actual (ASESPREV = módulos OTROS, no el mismo).
        # Celdas vacías deben dejar el campo vacío (como en Kobo), no forzar "Medicina General" vía _norm_servicio("").
        raw_asesp = str(record.get("ASESPREV", "")).strip()
        if raw_asesp:
            if "|||" in raw_asesp:
                partes: list[str] = []
                for p in raw_asesp.split("|||"):
                    v = _norm_asesprev_celda(p)
                    if v:
                        partes.append(v)
                if partes:
                    out["ASESPREV"] = "|||".join(partes)
            else:
                v_asp = _norm_asesprev_celda(raw_asesp)
                if v_asp:
                    out["ASESPREV"] = v_asp

    # ── OFTALMOLOGÍA: campos condicionales ───────────────────────────────────
    # Activar cuando el SERVICIO ACTUAL es Oftalmología (no cuando es asesoría previa).
    _servicio_oft = _norm_str(out.get("Servicio_que_se_brinda", ""))
    if "oftalmolog" in _servicio_oft:
        # 1. Síntomas → seleccionar Ardor, Comezón e Irritación por defecto
        out["S_ntomas_que_presenta_a_la_fec"] = OFT_SINTOMAS_DEFAULT

        # 2. Diagnóstico previo → Ninguno por defecto
        out["_Ha_recibido_alg_n_diagn_stico"] = "Ninguno"

        # 3. Diagnóstico actual → mapear desde el Excel
        diagnostico_oft_raw = str(record.get("Diagnostico_Motivo", "")).strip()
        if diagnostico_oft_raw:
            dx_oft, otro_dx = _map_diagnostico_oftalmologia(diagnostico_oft_raw)
            if dx_oft:
                out["Diagn_stico_002"] = dx_oft
            if otro_dx:
                out["Otro_diagn_stico"] = otro_dx

        # 4. ¿Requiere anteojos?
        # Prioridad: columna explícita del Excel → detección automática por insumos/tratamiento
        anteojos_excel = _parse_si_no(record.get("_Requiere_anteojos", ""))
        if anteojos_excel:
            out["_Requiere_anteojos"] = "Si" if anteojos_excel == "1" else "No"
        else:
            insumos_oft = str(record.get("Resultados_Lab_Insumos", "")).strip().lower()
            tx_oft = str(record.get("Tratamiento", "")).strip().lower()
            _dio_lentes = _tiene_lentes(insumos_oft) or _tiene_lentes(tx_oft)
            out["_Requiere_anteojos"] = "Si" if _dio_lentes else "No"

        # 5. Especifique qué se entrega → "Anteojos" cuando se dan lentes
        if out.get("_Requiere_anteojos") == "Si":
            out["Especifique_qu_se_entrega"] = "Anteojos"

    # ── ODONTOLOGÍA: campos condicionales ────────────────────────────────────
    # Activar cuando el SERVICIO ACTUAL es Dental/Odontología.
    _servicio_dental = _norm_str(out.get("Servicio_que_se_brinda", ""))
    if "dental" in _servicio_dental or "odontolog" in _servicio_dental:
        # 1. Diagnóstico dental → mapear desde Diagnostico_Motivo del Excel
        diagnostico_dental_raw = str(record.get("Diagnostico_Motivo", "")).strip()
        if diagnostico_dental_raw:
            dx_dental, dx_dental_esp = _map_diagnostico_dental(diagnostico_dental_raw)
            if dx_dental:
                out["Diagn_stico_001"] = dx_dental
            if dx_dental_esp:
                out["Especificar_002"] = dx_dental_esp

        # 2. ¿Se realiza procedimiento odontológico?
        # Prioridad: columna explícita → inferencia por insumos/referencia → "Si" por defecto
        proc_excel = _parse_si_no(record.get("_Se_realiza_procedimiento_odon",
                                              record.get("procedimiento_odontologico", "")))
        if proc_excel:
            out["_Se_realiza_procedimiento_odon"] = "Si" if proc_excel == "1" else "No"
        else:
            # Inferir: si hay referencia por complicación dental o hay tratamiento/kit dental,
            # se asume que sí se realizó un procedimiento.
            insumos_dental = str(record.get("Resultados_Lab_Insumos", "")).strip().lower()
            tx_dental = str(record.get("Tratamiento", "")).strip().lower()
            ref_motivo = str(record.get("Motivo_referencia", "")).strip().lower()
            _hay_proc = (
                "kit dental" in insumos_dental
                or "extraccion" in tx_dental or "extracción" in tx_dental
                or "profilaxis" in tx_dental or "limpieza" in tx_dental
                or "obturaci" in tx_dental or "empaste" in tx_dental
                or "extraccion" in ref_motivo or "extracción" in ref_motivo
                or "dental" in ref_motivo
            )
            out["_Se_realiza_procedimiento_odon"] = "Si" if _hay_proc else "No"

        # 3. ¿Qué procedimiento se realiza? → desde nueva columna del Excel
        proc_raw = str(record.get("Procedimiento_dental", "")).strip()
        if proc_raw:
            proc_val, proc_esp = _map_procedimiento_dental(proc_raw)
            if proc_val:
                out["_Qupe_procedimiento_se_realiza"] = proc_val
            if proc_esp:
                out["Especificar_003"] = proc_esp

    # ── FISIOTERAPIA: Diagnóstico API 0/1 (Diagnóstico/Revisión … /Otro) ───────
    _servicio_fisio = _norm_str(out.get("Servicio_que_se_brinda", ""))
    if "fisioterapia" in _servicio_fisio:
        dx_text = str(
            _pick_first(
                record,
                [
                    "Fisio_Diagnostico",
                    "Fisioterapia",
                    "Diagnostico_Fisioterapia",
                    "Diagnóstico_Fisioterapia",
                    "Diagnostico_fisioterapia",
                    "Diagnóstico fisioterapia",
                    "Diagnóstico en Fisioterapia",
                    "Diagnosticos",
                    "Diagnóstico",
                    "Diagnostico_Motivo",
                    "Diagnostico",
                ],
            )
            or ""
        ).strip()
        flags = _fisio_flags_from_text(dx_text) if dx_text else set()
        for fk in FISIO_BIN_KEYS:
            vrec = record.get(fk, "")
            if vrec is not None and str(vrec).strip() != "":
                out[fk] = _fisio_cell_to_01(vrec)
            else:
                out[fk] = "1" if fk in flags else "0"
        if out.get("FISIO_Otro") == "1":
            esp = str(record.get("Especificar", "")).strip() or dx_text
            if esp:
                out["Especificar"] = esp

        plan_tx = _pick_first(record, [
            "Plan_de_Tratamiento",
            "Plan de Tratamiento",
            "PlanTratamiento",
            "Tratamiento",
        ])
        if plan_tx:
            out["Plan_de_Tratamiento"] = plan_tx

        # Entrega de tratamiento e insumos
        entrega = _parse_si_no(record.get("entrega_tx", record.get("¿Se hizo entrega de tratamiento/artículos al beneficiario o beneficiaria?", "")))
        if entrega:
            out["entrega_tx"] = "1" if entrega == "1" else "0"
        insumos = _pick_first(record, ["Especifique_qu_se_entrega", "Insumos Entregados", "Especificar_lo_que_se_entrega_"])
        if insumos:
            out["Especifique_qu_se_entrega"] = insumos
            out["Especificar_lo_que_se_entrega_"] = insumos
        unidades = str(record.get("Unidades_entregadas", "")).strip()
        if unidades:
            out["Unidades_entregadas"] = unidades

    # ── FECHA ────────────────────────────────────────────────────────────────
    fecha_atencion = _norm_fecha(record.get("Fecha_de_atenci_n", ""))
    out["Fecha_de_atenci_n"] = fecha_atencion

    # ── INFORMACIÓN PERSONAL ─────────────────────────────────────────────────
    name_raw = str(record.get("NAME", "")).strip()
    name_raw = re.sub(r'[\s\-]?\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*$', '', name_raw).strip()
    name_raw = re.sub(r'[\s\-]?\d{1,2}[-/]\d{1,2}[-/]\d{4}\s*$', '', name_raw).strip()
    out["NAME"] = name_raw.upper() if name_raw else ""
    out["SEX"] = _norm_sex(record.get("SEX", "")) or "Femenino"
    out["AGE"] = str(record.get("AGE", "")).strip()

    # ── EMBARAZO / LACTANCIA (ME_ML) ──────────────────────────────────────────
    # Solo aplica para pacientes femeninas; si es masculino, omitir.
    me_ml_val = _norm_me_ml(record.get("ME_ML", ""))
    if me_ml_val and out.get("SEX") != "Masculino":
        out["ME_ML"] = me_ml_val

    dob_raw = _norm_fecha(record.get("DOB", record.get("Fecha_nacimiento", "")))
    if dob_raw:
        out["DOB"] = dob_raw
    else:
        try:
            age = int(record.get("AGE", 0))
            out["DOB"] = (date.today().replace(year=date.today().year - age)).isoformat() if age > 0 else "1990-01-01"
        except (ValueError, TypeError):
            out["DOB"] = "1990-01-01"

    out["HEI"] = str(record.get("HEI", "")).strip()
    out["WEI"] = str(record.get("WEI", "")).strip()
    out["HPI"] = str(record.get("Diagnostico_Motivo", record.get("HPI", ""))).strip()
    # Servicio_que_se_brinda ya se establece arriba en el bloque de especialidades
    out["Especificar_lo_que_se_entrega_"] = str(record.get("Resultados_Lab_Insumos", "")).strip()

    # ── DISCAPACIDADES (DIS) ──────────────────────────────────────────────────
    # Prioridad: subcolumnas 0/1 (export Kobo: …/Motriz, etc.) → DIS_*; si no, texto Discapacidad.
    if _has_dis_flag_column_data(record):
        dis_val, dis_esp = _dis_from_binary_flags(record)
        if dis_val:
            out["DIS"] = dis_val
        if dis_esp:
            out["Especificar_discapacidad"] = dis_esp
    else:
        discapacidad_raw = str(record.get("Discapacidad", "")).strip()
        if discapacidad_raw:
            dis_val, dis_esp = _map_discapacidades(discapacidad_raw)
            if dis_val:
                out["DIS"] = _dis_internals_to_kobo_labels(dis_val)
            if dis_esp:
                out["Especificar_discapacidad"] = dis_esp

    # ── DIAGNÓSTICOS (DX) ────────────────────────────────────────────────────
    # Mapear el diagnóstico del Excel a las opciones del formulario.
    # Si está en la lista → marcar ese checkbox; si no → marcar "Otro" + dxesp.
    diagnostico_raw = str(record.get("Diagnostico_Motivo", "")).strip()
    if diagnostico_raw:
        dx_val, dxesp_val = _map_diagnosticos(diagnostico_raw)
        if dx_val:
            out["DX"] = dx_val
        if dxesp_val:
            out["dxesp"] = dxesp_val
    # Columna hoja hacia dxesp (nunca usar la clave genérica "Especificar" aquí: en Kobo
    # resuelve a NATOT / nacionalidad).
    if "fisioterapia" not in _norm_str(out.get("Servicio_que_se_brinda", "")):
        explic_mg = str(record.get("dxesp", "") or "").strip()
        if explic_mg and ("Otro" in str(out.get("DX", "")) or not out.get("DX")):
            out["dxesp"] = explic_mg
        if explic_mg and not out.get("DX"):
            out["DX"] = "Otro"

    # ── TRATAMIENTO ──────────────────────────────────────────────────────────
    # Prioridad: columna "Tratamiento" del Excel → "Insumos Entregados" → "Control"
    # NO se usa Diagnostico_Motivo como fallback: el diagnóstico no es el tratamiento.
    tx_text = (
        str(record.get("Tratamiento", "")).strip()
        or str(record.get("Resultados_Lab_Insumos", "")).strip()
    )
    out["TX"] = tx_text or "Control"

    # Plan de tratamiento:
    # 1) Priorizar columna explícita del archivo (Plan_de_Tratamiento / Plan de Tratamiento)
    # 2) Si no existe, usar fallback desde Tratamiento/TX.
    if not str(out.get("Plan_de_Tratamiento", "")).strip():
        plan_src = (
            str(record.get("Plan_de_Tratamiento", "")).strip()
            or str(record.get("Plan de Tratamiento", "")).strip()
            or str(record.get("PlanTratamiento", "")).strip()
            or str(record.get("Tratamiento", "")).strip()
            or tx_text.strip()
        )
        if not plan_src:
            plan_src = str(out.get("TX", "")).strip()
        if plan_src:
            out["Plan_de_Tratamiento"] = plan_src

    entrega_tipo = (
        str(out.get("Especifique_qu_se_entrega", "")).strip()
        or str(record.get("Especifique_qu_se_entrega", "")).strip()
    )
    if not entrega_tipo:
        _svc_norm = _norm_str(out.get("Servicio_que_se_brinda", ""))
        if "oftalmolog" in _svc_norm:
            entrega_tipo = "Anteojos"
        elif "dental" in _svc_norm or "odontolog" in _svc_norm:
            entrega_tipo = "Anteojos"
        elif "fisioterapia" in _svc_norm:
            entrega_tipo = "Plan de Tratamiento"
        elif "laboratorio" in _svc_norm:
            entrega_tipo = "Resultados de Laboratorio"
        elif "medicina" in _svc_norm or "general" in _svc_norm:
            entrega_tipo = "Medicamento/suplemento"
        else:
            entrega_tipo = "Otro"
    out["Especifique_qu_se_entrega"] = entrega_tipo

    unidades = str(record.get("Unidades_entregadas", "1")).strip()
    out["Unidades_entregadas"] = unidades or "1"

    # Entrega de tratamiento: del Excel "¿Entrega Tratamiento?" / "¿Entrega?" /
    # "¿Se hizo entrega de tratamiento/artículos al beneficiario o beneficiaria?"
    # El formulario muestra "Si" (sin tilde) y "No"
    entrega_excel = _parse_si_no(record.get("entrega_tx", record.get("Entrega_Tratamiento", "")))
    if entrega_excel:
        # Valor explícito en el Excel → usarlo directamente
        tiene_entrega = entrega_excel == "1"
    else:
        # Sin valor explícito → auto-detectar por medicamento o lentes
        insumos_txt = str(record.get("Resultados_Lab_Insumos", "")).strip().lower()
        tx_txt = str(record.get("Tratamiento", "")).strip().lower()
        tiene_entrega = _tiene_medicamento_o_lentes(insumos_txt) or _tiene_medicamento_o_lentes(tx_txt)
    # Si se requieren anteojos → la entrega es automáticamente "Si"
    if out.get("_Requiere_anteojos") == "Si":
        tiene_entrega = True
    out["entrega_tx"] = "Si" if tiene_entrega else "No"

    # ── LUGAR DE ATENCIÓN ────────────────────────────────────────────────────
    lugar = str(record.get("Lugar", record.get("PLACE", ""))).strip()

    estado_brigada = str(record.get("Estado_brigada", "")).strip()
    search_val = estado_brigada or lugar
    poc_value = _map_estado_to_value(search_val) if search_val else POC_OTRO

    out["POC"] = poc_value

    # Determinar el campo de Lugar de Atención según el estado seleccionado.
    # Cada estado tiene su propio radio condicional en el formulario.
    lugar_field, lugar_value, lugar_es_otro = _map_lugar_atencion(poc_value, lugar)

    mod_k = str(out.get("Modalidad_de_la_atenci_n", "1") or "1")
    sch_excel = str(record.get("SCH", "")).strip()
    if poc_value == POC_OTRO:
        # Estado desconocido: llenar OTH/PLACE; SCH solo con modalidad Escuelas
        texto_libre = estado_brigada or lugar or "No especificado"
        out["OTH"] = texto_libre
        out["PLACE"] = texto_libre
        if mod_k == "escuelas":
            out["SCH"] = sch_excel or texto_libre
    elif lugar_field:
        # Estado conocido: seleccionar el radio del lugar correspondiente
        out[lugar_field] = lugar_value
        out["OTH"] = lugar    # Especificar Lugar de Atención
        out["PLACE"] = lugar
        if mod_k == "escuelas":
            out["SCH"] = sch_excel or lugar

    # ── UBICACIÓN GEOGRÁFICA ─────────────────────────────────────────────────
    # Prioridad:
    #   1. Columnas Latitud + Longitud explícitas en el Excel  → usar directamente
    #   2. Columna Ubicacion_geografica ya con formato "lat lon alt prec"
    #   3. Coordenadas guardadas previamente para este lugar (persistentes)
    #   4. Geocodificación automática por nombre de lugar (Nominatim + fallback)
    lat_excel = str(record.get("Latitud", record.get("lat", ""))).strip()
    lon_excel = str(record.get("Longitud", record.get("long", ""))).strip()
    lookup_lugar = lugar or estado_brigada
    coords = ""
    coords_source = ""
    if lat_excel and lon_excel:
        coords = f"{lat_excel} {lon_excel} 0 0"
        coords_source = "record"
    else:
        ubicacion_raw = str(record.get(
            "Ubicacion_geografica",
            record.get("Ubicaci_n_geogr_fica_de_la_atenci_n",
                       record.get("Coordenadas", ""))
        )).strip()
        lat_p = lon_p = alt_p = acc_p = ""
        if ubicacion_raw:
            lat_p, lon_p, alt_p, acc_p = parse_coords_string(ubicacion_raw)
        if lat_p and lon_p:
            coords = f"{lat_p} {lon_p} {alt_p or '0'} {acc_p or '0'}".strip()
            coords_source = "record"
        else:
            # Coordenadas persistidas para este lugar (si el usuario las capturó antes)
            stored = get_coords_for_lugar(lookup_lugar) if lookup_lugar else None
            if stored:
                coords = coords_to_string(stored)
                coords_source = "stored"
            else:
                # Geocodificar por nombre: primero el lugar, luego el estado de brigada
                busqueda = ubicacion_raw or lugar or estado_brigada
                coords = _geocodificar(busqueda) if busqueda else ""
                coords_source = "geocode" if coords else ""

    if coords:
        out["Ubicaci_n_geogr_fica_de_la_atenci_n"] = coords
        # Persistir coordenadas para el lugar (no sobrescribe manual con geocode)
        if lookup_lugar:
            lat_s, lon_s, alt_s, acc_s = parse_coords_string(coords)
            if lat_s and lon_s:
                upsert_coords_for_lugar(
                    lookup_lugar,
                    lat_s,
                    lon_s,
                    alt_s or "0",
                    acc_s or "0",
                    source="manual" if coords_source in ("record", "stored") else "geocode",
                )

    # ── PRIMERA VEZ / SEGUIMIENTO ─────────────────────────────────────────────
    # Valores reales del formulario: "1"=Primera vez, "2"=Seguimiento,
    #                                "3"=Atención Única, "4"=Entrega de Insumos
    followup_raw = str(record.get("followup", record.get("Primera_vez_seguimiento", ""))).strip().lower()
    if "única" in followup_raw or "unica" in followup_raw:
        out["followup"] = "3"   # Atención Única
    elif "seguimiento" in followup_raw:
        out["followup"] = "2"   # Seguimiento
    elif "insumo" in followup_raw or "entrega" in followup_raw:
        out["followup"] = "4"   # Entrega de Insumos
    else:
        out["followup"] = "1"   # Primera vez (default)

    # ── ACOMPAÑANTE ──────────────────────────────────────────────────────────
    acompanante = str(record.get("CGR", "")).strip()
    if acompanante:
        out["CGR"] = acompanante
    else:
        try:
            age = int(record.get("AGE", 99))
            out["CGR"] = "Cuidadora mujer" if age < 18 else ""
        except (ValueError, TypeError):
            pass

    # ── ESTATUS MIGRATORIO ───────────────────────────────────────────────────
    estatus = str(record.get("estatus_migra", "")).strip()
    out["estatus_migra"] = estatus or "Ciudadano Mexicano"

    # ── REFERENCIAS ──────────────────────────────────────────────────────────
    ref_parsed = _parse_si_no(
        str(record.get("Referencia", record.get("REF", ""))).strip()
    )
    hizo_ref = ref_parsed == "1"
    out["REF"] = "Sí" if hizo_ref else "No"
    if hizo_ref:
        ref_donde = str(record.get("Referencia_donde", "Clínica")).strip().lower()
        reforg_map = {
            "segundo nivel":       "Segundo Nivel de Atención/Especialidad",
            "especialidad":        "Segundo Nivel de Atención/Especialidad",
            "ong":                 "ONG",
            "ministerio público":  "Ministerio público",
            "ministerio publico":  "Ministerio público",
            "mp":                  "Ministerio público",
            "clínica":             "Clínica",
            "clinica":             "Clínica",
        }
        out["REFORG"] = reforg_map.get(ref_donde, "Clínica")
        ref_spec = str(record.get("Referencia_especificar", "")).strip()
        if not ref_spec and ("clínica" in ref_donde or "clinica" in ref_donde):
            ref_spec = "Clínica Adventista"
        out["REFSPEC"] = ref_spec or "Clínica Adventista"
        motivo = str(record.get("Motivo_referencia", "Otro")).strip()
        out["MEDREF"] = MOTIVO_REFERENCIA.get(motivo.lower(), "Otro")
        if out["MEDREF"] == "Otro":
            out["SPREFMOTMED"] = str(record.get("Motivo_especificar", "No especificado")).strip()

    # ── ESTADO DEL PACIENTE (campo Estado, dropdown de estados mexicanos) ────────
    # Leer directamente de la columna "Estado paciente" / "Estado.1" del Excel.
    # Fallback: si no viene ese campo, usar el estado de la brigada (POC).
    estado_paciente_raw = str(record.get("Estado_paciente", "")).strip()
    if estado_paciente_raw:
        out["Estado"] = _norm_estado_paciente(estado_paciente_raw)
    elif poc_value != POC_OTRO:
        out["Estado"] = ESTADO_LABEL_FROM_VALUE.get(poc_value, "")
    # Si ninguno disponible, dejar vacío (el formulario lo dejará sin selección)

    return {k: v for k, v in out.items() if v is not None and str(v) != ""}


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def _especialidad_marcada(val: str) -> bool:
    """
    Retorna True si una columna de especialidad del formulario físico tiene
    algún servicio marcado (valor positivo, texto no vacío, etc.).
    Retorna False si está vacía, es cero o indica explícitamente "no".
    """
    v = str(val or "").strip().lower()
    if not v or v in ("0", "no", "ninguno", "ninguno seleccionado", "-", "n/a", "na"):
        return False
    try:
        return float(v) > 0
    except ValueError:
        return True  # texto no vacío y no negativo = hay servicio marcado


def _pick_first(record: dict, keys: list[str]) -> str:
    """Devuelve el primer valor no vacío de las claves dadas."""
    for k in keys:
        v = record.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _map_estado_to_value(estado: str) -> str:
    """
    Retorna el VALUE real del formulario para el campo POC (radio).
    Si no coincide con ningún estado conocido → POC_OTRO ("4").
    """
    if not estado:
        return POC_OTRO
    e = estado.lower().strip()
    for key, val in ESTADO_TO_FORM_VALUE.items():
        if key in e:
            return val
    return POC_OTRO


def _norm_estado_paciente(s: str) -> str:
    """
    Normaliza el nombre del estado del paciente al valor exacto del formulario.
    Usa comparación sin tildes para mayor robustez.
    """
    s = str(s or "").strip()
    if not s:
        return ""
    s_norm = _norm_str(s)
    # Búsqueda exacta primero (sin tildes)
    for key, val in ESTADO_PACIENTE_ALIAS.items():
        if _norm_str(key) == s_norm:
            return val
    # Búsqueda por contenido parcial (el texto contiene al estado o viceversa)
    for key, val in ESTADO_PACIENTE_ALIAS.items():
        k_norm = _norm_str(key)
        if k_norm and len(k_norm) > 3 and (k_norm in s_norm or s_norm in k_norm):
            return val
    # Si no coincide: devolver el texto original con capitalización corregida
    return s.title()


_FECHA_INVALID = {"n/d", "nd", "na", "n/a", "no disponible", "no aplica", "sin fecha", ""}


def _norm_fecha(s: str) -> str:
    """Convierte cualquier formato de fecha a YYYY-MM-DD para KoboToolbox."""
    s = str(s or "").strip()
    if not s or s.lower() in _FECHA_INVALID:
        return ""
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", s)
    if m:
        d, mes, y = m.groups()
        y = "20" + y if len(y) == 2 else y
        return f"{y}-{mes.zfill(2)}-{d.zfill(2)}"
    try:
        n = float(s.split()[0] if " " in s else s)
        if 1000 < n < 100000:
            from datetime import timedelta
            excel_epoch = date(1899, 12, 30)
            d = excel_epoch + timedelta(days=int(n))
            return d.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return s


def _preparse_excel_yesno(s: str) -> str:
    """
    Limpia valores de Excel/CSV típicos antes de interpretar Sí/No:
    - Sufijos tipo \"Sí +1\"
    - Carácter de reemplazo UTF-8 (p. ej. S\uFFFD → Sí) por codificación mala
    - Cadenas \"no dato\" (se devuelve vacío para dejar heurísticas / defaults)
    """
    t = str(s or "").strip()
    if not t:
        return ""
    t = re.sub(r"\s*\+\d+\s*$", "", t, flags=re.IGNORECASE)
    t = t.strip()
    if len(t) >= 2 and t[0] in "Ss" and t[1] == "\ufffd":  # U+FFFD (S� por UTF-8 roto)
        t = t[0] + "í" + t[2:]
    low = t.lower()
    if low in {
        "n/d",
        "n / d",
        "n/d",
        "nd",
        "n d",
        "n.d",
        "n.d.",
        "na",
        "n a",
        "-",
        "—",
        "–",
    }:
        return ""
    return t


def _parse_si_no(s: str) -> str:
    """Sí/No/SI/NO/1/0/true/false/verdadero/falso → '1' o '0' (vacío = no interpretable)."""
    t = _preparse_excel_yesno(s)
    v = t.lower()
    v = v.replace("sí", "si")
    v = re.sub(r"\s+", " ", v).strip()
    if v in (
        "si",
        "s",
        "yes",
        "y",
        "1",
        "true",
        "t",
        "verdadero",
    ):
        return "1"
    if v in ("no", "n", "0", "false", "f", "falso"):
        return "0"
    if len(v) == 1 and v in ("1", "0"):
        return v
    return ""


def _norm_sex(s: str) -> str:
    """F/M/H/Female/Male/Femenino/Masculino → Femenino/Masculino."""
    s = str(s or "").strip().upper()
    if not s:
        return ""
    # Femenino — lista explícita sin condiciones genéricas
    if s in ("F", "FEMALE", "FEMENINO", "MUJER", "FEM", "FEMENI"):
        return "Femenino"
    if "FEMENIN" in s or "MUJER" in s or "FEMALE" in s:
        return "Femenino"
    # Masculino — lista explícita sin condiciones genéricas
    if s in ("M", "MALE", "MASCULINO", "HOMBRE", "MASC", "H"):
        return "Masculino"
    if "MASCULIN" in s or "HOMBRE" in s or "MALE" in s:
        return "Masculino"
    return ""


# Variaciones de servicio → etiquetas exactas del formulario
SERVICIO_ALIAS = {
    # Medicina General
    "medicina general":   "Medicina General",
    "medicina":           "Medicina General",
    "med general":        "Medicina General",
    "medico":             "Medicina General",
    "médico":             "Medicina General",
    "consulta":           "Medicina General",
    # Dental / Odontología
    "dental":             "Dental",
    "odontologia":        "Dental",
    "odontología":        "Dental",
    "odonto":             "Dental",
    # Fisioterapia
    "fisioterapia":       "Fisioterapia",
    "fisio":              "Fisioterapia",
    "fiosterapia":        "Fisioterapia",   # typo frecuente
    "terapia fisica":     "Fisioterapia",
    "terapia física":     "Fisioterapia",
    "rehabilitacion":     "Fisioterapia",
    "rehabilitación":     "Fisioterapia",
    # Oftalmología
    "oftalmologia":       "Oftalmología",
    "oftalmología":       "Oftalmología",
    "oftalmologica":      "Oftalmología",
    "optica":             "Oftalmología",
    "óptica":             "Oftalmología",
    "vision":             "Oftalmología",
    "visión":             "Oftalmología",
    "lentes":             "Oftalmología",
    # Laboratorios
    "laboratorio":        "Laboratorios",
    "laboratorios":       "Laboratorios",
    "lab":                "Laboratorios",
    "labs":               "Laboratorios",
    "examenes":           "Laboratorios",
    "exámenes":           "Laboratorios",
}

# Etiquetas exactas del formulario Kobo (para priorizar columna "Servicio que se brinda")
SERVICIOS_CANONICOS = frozenset(SERVICIO_ALIAS.values())


def _norm_servicio(s: str) -> str:
    """Normaliza el valor de servicio del Excel al valor exacto del formulario KoboToolbox.

    Si el valor no coincide con ningún servicio conocido, retorna "Medicina General".
    """
    s = str(s or "").strip()
    s = re.sub(r"\s*\+\d+\s*$", "", s).strip()
    if not s:
        return "Medicina General"
    # Búsqueda exacta (sin tildes para robustez)
    s_norm = _norm_str(s)
    for key, val in SERVICIO_ALIAS.items():
        if _norm_str(key) == s_norm:
            return val
    # Búsqueda por contenido parcial (el valor contiene la clave)
    for key, val in SERVICIO_ALIAS.items():
        if _norm_str(key) in s_norm and len(_norm_str(key)) > 3:
            return val
    return "Medicina General"


def _norm_asesprev_celda(s: str) -> str:
    """
    Una celda de ASESPREV: módulo del formulario o la opción explícita «No Aplica».
    Nunca pasa cadenas vacías por _norm_servicio (que convertiría '' en «Medicina General»).
    """
    t = str(s or "").strip()
    if not t:
        return ""
    n = _norm_str(t)
    if t == "No Aplica" or n in (
        "no aplica",
        "no_aplica",
        "n/a",
        "n a",
        "na",
        "n d",
        "nd",
        "ninguno",
        "ninguna",
        "n/d",
    ):
        return "No Aplica"
    return _norm_servicio(t)


# Opciones válidas del formulario para ME_ML (¿Mujer embarazada o en periodo de lactancia?)
# path: /aD6FdrTDPaW4QzCLjmG7WE/group_py4vt65/ME_ML
ME_ML_ALIAS: dict[str, str] = {
    # Embarazada
    "embarazada":       "Embarazada",
    "embarazo":         "Embarazada",
    "gestante":         "Embarazada",
    "gestacion":        "Embarazada",
    "gestación":        "Embarazada",
    "si embarazada":    "Embarazada",
    # Lactancia
    "lactancia":        "Lactancia",
    "lactante":         "Lactancia",
    "amamantando":      "Lactancia",
    "lactando":         "Lactancia",
    "periodo de lactancia": "Lactancia",
    # No aplica
    "no aplica":        "No Aplica",
    "no_aplica":        "No Aplica",
    "no":               "No Aplica",
    "ninguna":          "No Aplica",
    "n/a":              "No Aplica",
    "na":               "No Aplica",
}


# ── Oftalmología ─────────────────────────────────────────────────────────────
# Síntomas predeterminados cuando el servicio es Oftalmología
OFT_SINTOMAS_DEFAULT = "Ardor|||Comezón|||Irritación"

# Opciones válidas de Diagnóstico Previo (¿Ha recibido algún diagnóstico previo?)
OFT_DX_PREVIO_OPTIONS = [
    "Ninguno",
    "Catarata",
    "Glaucoma",
    "Estrabismo",
    "Retinopatía",
    "Pterigión",
    "Otro",
]

# Opciones válidas de Diagnóstico Actual en el formulario de Oftalmología
OFT_DX_ACTUAL_OPTIONS = [
    "Ametropía",
    "Miopía",
    "Astigmatismo",
    "Hipermetropía",
    "Estabismo",
    "Otro",
]


def _map_diagnostico_oftalmologia(text: str) -> tuple[str, str]:
    """
    Mapea el texto de diagnóstico del Excel a las opciones del formulario de Oftalmología
    (campo Diagnóstico Actual / Diagn_stico_002).

    Retorna (dx_value, otro_dx):
      dx_value → etiqueta coincidente (ej. "Miopía") o "Otro" si no coincide
      otro_dx  → texto libre para el campo Otro_diagn_stico si no hay coincidencia
    """
    text = str(text or "").strip()
    if not text:
        return "", ""

    # Pre-calcular versiones normalizadas sin "Otro"
    dx_norm = {_norm_str(opt): opt for opt in OFT_DX_ACTUAL_OPTIONS if opt != "Otro"}

    text_norm = _norm_str(text)
    for norm_opt, original_opt in dx_norm.items():
        if text_norm == norm_opt:
            return original_opt, ""
        if text_norm and len(text_norm) > 3 and text_norm in norm_opt:
            return original_opt, ""
        if norm_opt and len(norm_opt) > 3 and norm_opt in text_norm:
            return original_opt, ""

    # No coincidió → "Otro" con texto libre
    return "Otro", text


def _norm_me_ml(s: str) -> str:
    """Normaliza el valor de embarazo/lactancia al valor exacto del formulario."""
    s = str(s or "").strip()
    if not s:
        return ""
    s_norm = _norm_str(s)
    for key, val in ME_ML_ALIAS.items():
        if _norm_str(key) == s_norm:
            return val
    # Búsqueda parcial
    for key, val in ME_ML_ALIAS.items():
        if _norm_str(key) in s_norm or s_norm in _norm_str(key):
            return val
    return ""


# Palabras clave que indican entrega de medicamento o lentes
_KEYWORDS_MEDICAMENTO = {
    "medicamento", "medicina", "med ", "meds", "pastilla", "tableta", "cápsula", "capsula",
    "antibiótico", "antibiotico", "vitamina", "suplemento", "jarabe", "crema", "pomada",
    "hierro", "ácido fólico", "acido folico", "amoxicilina", "ibuprofeno", "paracetamol",
    "ampicilina", "fármaco", "farmaco", "tratamiento", "antihipertensivo", "antiparasitario",
    "antifúngico", "antifungico", "acetaminofen", "acetaminofén", "omeprazol", "metformina",
    "insulina", "salbutamol", "prednisolona", "dexametasona", "albendazol", "multivitaminico",
    "multivitamínico",
}
_KEYWORDS_LENTES = {
    "lentes", "armazón", "armazon", "anteojos", "óptica", "optica",
    "graduación", "graduacion", "montura", "bifocal",
}


def _tiene_lentes(texto: str) -> bool:
    """Retorna True si el texto menciona lentes/anteojos (sin requerir medicamentos)."""
    if not texto:
        return False
    t = texto.lower()
    for kw in _KEYWORDS_LENTES:
        if kw in t:
            return True
    return False


def _tiene_medicamento_o_lentes(texto: str) -> bool:
    """
    Retorna True si el texto menciona entrega de medicamento o lentes.
    Ignora resultados de laboratorio (glucosa, colesterol, etc.).
    """
    if not texto:
        return False
    t = texto.lower()
    for kw in _KEYWORDS_MEDICAMENTO:
        if kw in t:
            return True
    for kw in _KEYWORDS_LENTES:
        if kw in t:
            return True
    return False
