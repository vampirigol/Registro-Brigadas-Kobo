# Opción: Enviar datos vía API KoboToolbox (sin navegador)

Si el llenado por Playwright sigue fallando, puedes usar la **API de KoboToolbox** para enviar datos directamente (sin abrir navegador).

## Requisitos

1. **Token de API** de KoboToolbox:
   - Entra a tu cuenta en https://eu.kobotoolbox.org (o kf.kobotoolbox.org)
   - Perfil → Account Settings → Security → API Key → Display

2. **Asset UID** del proyecto:
   - Abre tu proyecto en KoboToolbox
   - En la URL verás: `...#/forms/[ASSET_UID]/summary`
   - Copia ese ASSET_UID (ej: `aD6FdrTDPaW4QzCLjmG7WE`)

## Configuración

En el archivo `.env`:
```
KOBO_API_TOKEN=tu_token_aqui
KOBO_ASSET_UID=tu_asset_uid
```

## Uso

Si configuras token y asset UID, la app puede intentar enviar vía API en lugar de Playwright (funcionalidad pendiente de implementar). Por ahora, el llenado sigue siendo por Playwright con la mejora página por página.
