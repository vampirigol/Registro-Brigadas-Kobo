# Cómo hacer el llenado automático más preciso

## 1. Enviar por API KoboToolbox (recomendado)

**No hace falta instalar ninguna extensión.** La app puede enviar los datos directamente al servidor de KoboToolbox por API. Así no se usa el navegador ni se simulan clics; los datos se envían en XML y la precisión es máxima.

### Pasos

1. Obtén tu **token de API** en KoboToolbox: Perfil → Account Settings → Security → API Key.
2. Copia el **Asset UID** de tu proyecto (está en la URL del formulario/proyecto, ej. `aD6FdrTDPaW4QzCLjmG7WE`).
3. En la carpeta del proyecto crea o edita el archivo `.env` y añade:
   ```
   KOBO_API_TOKEN=tu_token_aqui
   KOBO_ASSET_UID=tu_asset_uid
   ```
   Si usas el servidor EU: `KOBO_KC_URL=https://kc-eu.kobotoolbox.org`
4. Reinicia la app (`./run.sh`).
5. En la pantalla **3. Iniciar carga** aparecerá la opción **"Enviar por API KoboToolbox"**. Márcala y pulsa **Iniciar carga**.

Los datos se enviarán por HTTP al servidor; no se abrirá el navegador. Es el método más preciso.

Ver también: [OPCION_API_KOBO.md](OPCION_API_KOBO.md).

---

## 2. Llenado en navegador (Playwright)

Si no configuras la API, la app sigue usando el navegador (Playwright) y rellena el formulario con inyección de JavaScript en el iframe. Ya se intentan valores alternativos (p. ej. "Móvil"/"movil", "1"/"Sí" para consentimiento) y se marcan por defecto CONS1, Modalidad, Estado, Primera vez/Seguimiento y Asesoría.

---

## 3. Extensiones de navegador

No hay una extensión estándar que rellene formularios KoboToolbox de forma más precisa que la opción API. Lo que hace la app (inyección de JS en el iframe desde Playwright) es el equivalente técnico a una extensión que actuara sobre el formulario.

Si en el futuro quisieras usar algo como **Tampermonkey** para rellenar el formulario cuando lo abres a mano, tendrías que escribir un script que se ejecute en el dominio del formulario (ee-eu.kobotoolbox.org) y que reciba los datos (p. ej. por `postMessage` desde otra pestaña). Es más trabajo de mantenimiento y no es necesario si usas la API.

---

**Resumen:** Para mayor precisión, usa **Enviar por API KoboToolbox** configurando `KOBO_API_TOKEN` y `KOBO_ASSET_UID` en `.env`.
