# Instrucciones para probar el llenado automático

## 1. Crear el Excel de prueba

```bash
python create_excel_prueba.py
```

Se crea `excel_de_prueba.xlsx` con 1 fila de datos de paciente (Sandra Murillo Espinoza).

## 2. Iniciar la aplicación

```bash
./run.sh
```

Abre http://localhost:5001 en el navegador.

## 3. Probar el llenado

1. En la app, sube el archivo `excel_de_prueba.xlsx` (arrastra o haz clic en la zona de subida).
2. Opcional: en "2. Verificar datos" revisa que se muestren los datos correctos.
3. En "3. Iniciar carga", completa **Estado de la brigada** (ej. Baja California Sur) y **Lugar** (ej. Santa Rosalía) si quieres sobrescribir.
4. Pulsa **Iniciar carga**.

La ventana se abrirá automáticamente y debería ir llenando el formulario con los datos del Excel.

## 4. Alternativa: prueba directa por script

```bash
# Con la app corriendo en otra terminal (./run.sh)
python run_llenado_prueba.py
```

Esto ejecuta el llenado de 1 fila usando `excel_de_prueba.xlsx` sin pasar por la interfaz web.

## Archivos de prueba

- `excel_de_prueba.xlsx`: Excel con columnas del formulario y 1 paciente de ejemplo.
- `create_excel_prueba.py`: Script que genera el Excel de prueba.
- `run_llenado_prueba.py`: Script de prueba directa del llenado.

## Si algo falla

1. Revisa la terminal donde corre `./run.sh` por mensajes de error.
2. Asegúrate de que la ventana que se abre muestra la app (localhost:5001) con el formulario KoboToolbox cargado en el iframe.
3. Si el formulario no carga, espera unos segundos; KoboToolbox puede tardar.
4. Verifica que la URL del formulario en `config.py` o `.env` (FORM_URL) sea la correcta.
