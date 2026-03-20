# Carga por API KoboToolbox (recomendado)

El llenado automático del formulario con el navegador (Playwright) es frágil: iframes, nombres de campos que cambian y validaciones de Enketo hacen que falle con frecuencia.

**Solución estable:** usar la API de KoboToolbox. Tu proyecto ya tiene el módulo `kobo_api.py` y el runner lo usa automáticamente si configuras las variables de entorno.

## Pasos para usar la API

### 1. Obtener el API Token

1. Entra en [KoboToolbox](https://kobotoolbox.org/) e inicia sesión.
2. Ve a **Cuenta** (o **Account**) → **API Token**.
3. Crea un token si no tienes uno y cópialo.

### 2. Obtener el Asset UID del formulario

- Opción A: En [Kobo Form Builder](https://kf.kobotoolbox.org/) (o kf-eu si usas el servidor EU), abre tu formulario. El **UID** del asset suele aparecer en la URL o en la configuración del formulario.
- Opción B: Desde la API de KoBoCat: `GET https://kc.kobotoolbox.org/api/v1/forms` (o `kc-eu.kobotoolbox.org` si tu formulario está en EU) con el header `Authorization: Token TU_TOKEN`. En la respuesta, localiza el formulario por nombre y copia el campo `uid` o el que identifique el asset.

Si tu formulario está en **ee-eu.kobotoolbox.org**, el servidor de envío suele ser **kc-eu.kobotoolbox.org**.

### 3. Configurar `.env`

Copia `.env.example` a `.env` (si no lo tienes) y añade o edita:

```env
KOBO_API_TOKEN=tu_token_aqui
KOBO_ASSET_UID=el_uid_del_formulario
# Si usas el servidor EU (formulario en ee-eu):
KOBO_KC_URL=https://kc-eu.kobotoolbox.org
```

### 4. Ejecutar la carga

Al ejecutar `./run.sh` (o el script que uses), el runner detecta que hay token y asset UID y **usa la API en lugar del navegador**. Verás un mensaje como: *"Usando envío por API KoboToolbox (sin navegador)."*

Los datos del Excel se envían en XML al endpoint de submissions; no se abre ninguna ventana del navegador y no dependes del llenado campo a campo en Enketo.

## Referencias

- [KoboToolbox API – Getting started](https://support.kobotoolbox.org/api.html)
- [Adding Submissions via API (comunidad)](https://community.kobotoolbox.org/t/adding-submissions-to-kobo-toolbox-using-submissions-endpoint/7526)
