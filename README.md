# Llenado Kobo Tools

Herramienta para automatizar la carga masiva de registros desde un archivo Excel hacia formularios web de KoboToolbox (Enketo), simulando interacción humana para preservar validaciones y lógica de saltos.

## Requisitos

- Python 3.10+
- Chromium (se instala vía Playwright)

## Instalación

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium
```

(Alternativa: si tienes `python` o `pip` sin restricciones, puedes usar `pip install -r requirements.txt` y `playwright install chromium` directamente.)

## Configuración

1. Copia `.env.example` a `.env` y ajusta:
   - `FORM_URL`: URL del formulario Enketo
   - `EXCEL_PATH`: ruta al archivo `datos.xlsx`
   - `HEADLESS`: `true` para ejecutar sin ventana visible, `false` para ver el navegador
   - `RESUME_FROM_ROW`: (opcional) fila desde la cual reanudar (0-indexed)

2. Configura el mapeo de columnas:
   - Ejecuta `python discover_form.py` para extraer los campos del formulario
   - Copia el contenido de `mapping_discovered.yaml` a `mapping.yaml`
   - Ajusta los nombres de la izquierda para que coincidan con las columnas de tu Excel

## Uso

### Opción A: Interfaz web (recomendado)

Puedes subir el Excel, ver la configuración y lanzar la carga desde el navegador, viendo el progreso paso a paso:

```bash
./run.sh
```

O manualmente con el venv:
```bash
./venv/bin/python server.py
```

Abre **http://localhost:5001** en el navegador (puerto 5001 para evitar conflicto con AirPlay en macOS). Ahí podrás:

1. **Subir el Excel**: arrastra `datos.xlsx` o selecciona el archivo.
2. **Iniciar**: haz clic en "Iniciar". Se abrirá una ventana de Chromium con el formulario de KoboToolbox; en esa ventana verás el llenado en vivo. En la página web verás el progreso fila por fila (éxitos, fallidos, tiempo).

Asegúrate de tener `mapping.yaml` configurado (ejecuta `discover_form.py` y copia el mapeo).

### Opción B: Línea de comandos

```bash
python main.py
```

El script lee `datos.xlsx` fila por fila, rellena el formulario, envía cada registro y continúa con el siguiente. Los errores se registran en `logs/errores.log` y las estadísticas finales en `logs/estadisticas.json`.

## Estructura del Proyecto

```
├── .env                 # Configuración (no commitear)
├── .env.example         # Plantilla de configuración
├── requirements.txt
├── mapping.yaml         # Mapeo columnas Excel → campos Enketo
├── config.py            # Carga de configuración
├── excel_reader.py      # Lectura del Excel
├── form_filler.py       # Llenado con Playwright
├── main.py              # Orquestador principal (CLI)
├── server.py            # Servidor web para interfaz de carga
├── runner.py            # Ejecutor con callback de progreso
├── discover_form.py     # Extrae estructura del formulario
├── static/              # Frontend (HTML, CSS, JS)
├── uploads/             # Excel subidos desde la interfaz
├── utils/
│   └── selectors.py     # Selectores CSS
├── logs/
│   ├── errores.log      # Log de errores
│   └── estadisticas.json # Resumen final
└── README.md
```

## Modo Reanudar

Si el proceso se interrumpe, configura `RESUME_FROM_ROW` en `.env` con el número de fila (0-indexed) desde la cual continuar y vuelve a ejecutar `python main.py`.

## Consideraciones

- Los datos se convierten a string antes de escribirse en el formulario
- Si un registro falla, se registra el error y se continúa con el siguiente
- Se realizan hasta 3 intentos por registro ante fallos de red
- El formulario puede tener múltiples páginas; el script hace clic en "Next" automáticamente hasta llegar al botón "Submit"
