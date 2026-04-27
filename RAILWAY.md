# Desplegar en Railway

La pantalla **“What do you need?”** es de **[Railway](https://railway.app)**. Para este proyecto (Flask + herramientas de sistema) el flujo correcto es **conectar el repositorio de GitHub**, no solo “Database”.

## 1. Preparar el código en GitHub

1. Crea un repositorio en GitHub y sube esta carpeta del proyecto (sin `venv/`).
2. Confirma que en la raíz existen `Dockerfile`, `requirements.txt` y `server.py`.

## 2. Crear el proyecto en Railway

1. **New project** → **GitHub Repo** → elige el repositorio.
2. Railway detectará el **Dockerfile** y construirá la imagen automáticamente.
3. En **Settings → Networking** genera un **dominio público** (o usa el que asigne Railway).

## 3. Variables de entorno (mínimo útil)

En **Variables** del servicio, define al menos:

| Variable | Descripción |
|----------|-------------|
| `FORM_URL` | URL Enketo de tu formulario Kobo (ej. `https://ee-eu.kobotoolbox.org/x/...`). |
| `HEADLESS` | En el servidor no hay pantalla: usa `true`. |
| `USE_DIRECT_FORM_URL` | Recomendado `true` (comportamiento por defecto). |

**URL pública de la app:** si no pones `APP_URL`, el código usa `RAILWAY_PUBLIC_DOMAIN` (Railway la inyecta al desplegar). Si algo no cuadra con el iframe o Playwright, define manualmente:

`APP_URL=https://TU-DOMINIO.up.railway.app`

**Carga sin navegador (recomendado en la nube):** configura la API de Kobo para no depender de Chromium en el contenedor:

- `KOBO_API_TOKEN`
- `KOBO_ASSET_UID`
- `KOBO_KC_URL` (ej. `https://kc-eu.kobotoolbox.org` si tu proyecto está en la región EU)

Ver `.env.example` para el resto de opciones.

## 4. Despliegue

Tras el primer build correcto, Railway ejecuta Gunicorn escuchando en `PORT`. Abre la URL pública: deberías ver la interfaz web.

## Notas

- **“Database”** en ese menú sirve para añadir Postgres/MySQL, etc. Este servidor no exige base de datos para arrancar; solo el servicio desde **GitHub Repo** (o **Empty Service** + conectar repo después).
- Los archivos subidos y logs viven en el **filesystem efímero** del contenedor; si reinicia el servicio, pueden perderse salvo que añadas volumen o almacenamiento externo.
