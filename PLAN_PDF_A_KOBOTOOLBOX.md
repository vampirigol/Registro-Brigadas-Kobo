# Plan: Flujo PDF → KoboToolbox

## Resumen del flujo

```
1. Subir PDF
2. Extraer texto/tablas del PDF → tabla estructurada
3. Humano verifica y valida datos
4. Iniciar llenado en formulario web
5. Repetir formulario por especialidad (1 paciente × N especialidades = N formularios)
6. Pausar para validación en tiempo real si hay dudas
```

---

## Análisis técnico

### Estado del PDF de ejemplo

- **Ruta:** `Ligui 17-02-26 px 1-24.pdf`
- **Tipo:** PDF escaneado (imágenes), 24 páginas
- **Texto:** No hay capa de texto, requiere **OCR** (Tesseract)

### Requisitos de software para OCR

Para PDFs escaneados hace falta instalar en tu Mac:

```bash
brew install tesseract tesseract-lang
brew install poppler
```

Y en Python:

```
pdf2image, pytesseract, pillow
```

---

## Fases de implementación

### Fase 1: Subir PDF y extraer texto (OCR)

- Subir PDF en la interfaz web
- Detectar si es texto o imagen (escaneado)
- Texto: `pdfplumber` 
- Imagen: convertir a imágenes con `pdf2image` y aplicar `pytesseract`
- Guardar texto por página en la base de proceso

### Fase 2: Parser de campos (formulario médico BRIGADAS ADRA)

Depende del diseño exacto del PDF. Necesitamos:

- Ejemplo del PDF (o pantallazos de las páginas) con los campos
- Definir qué campos existen y cómo se identifican (regex, etiquetas, posición)
- Crear un mapeo PDF → columnas internas

**Pregunta:** ¿Tienes la plantilla o un ejemplo del formulario en Word/Excel que muestre dónde va cada dato? Eso ayudaría a definir el parser.

### Fase 3: Interfaz de verificación humana

- Mostrar tabla con datos extraídos
- Editar celdas directamente
- Marcar “válido” por fila o por campo
- Botón “Confirmar y continuar” solo cuando los datos estén validados

### Fase 4: Repetición por especialidad

- Detectar especialidades en el PDF (odontología, medicina general, oftalmología, laboratorio, etc.)
- Por cada paciente con N especialidades → generar N registros
- Cada registro = 1 envío al formulario KoboToolbox

### Fase 5: Validación en tiempo real durante el llenado

- Mientras Playwright rellena el formulario, si el script detecta ambigüedad:
  - Pausar
  - Mostrar modal en la web con el campo en duda
  - Usuario corrige o confirma
  - Reanudar llenado

---

## Información que necesito de ti

1. **Layout del PDF:** ¿Cómo es el formulario? ¿Hay tablas, secciones fijas, checkboxes por especialidad? Un pantallazo de 1–2 páginas ayudaría.
2. **Especialidades:** Lista exacta de especialidades (ej: Odontología, Medicina General, Oftalmología, Laboratorio clínico) y cómo se indican en el PDF (checkbox, texto, otra marca).
3. **Campos prioritarios:** Qué datos del PDF son esenciales para cada envío al formulario web (nombre, edad, especialidad, fecha, etc.).
4. **Mapeo PDF ↔ KoboToolbox:** ¿Los campos del PDF coinciden con los del formulario web o hay que transformarlos (ej: “Odontología” → código, fechas en otro formato, etc.)?

---

## Próximos pasos

1. Instalar Tesseract y Poppler en tu Mac (paso necesario para OCR).
2. Crear un script de prueba que extraiga texto del PDF de ejemplo.
3. Con el layout que me compartas, diseñar el parser de campos.
4. Implementar las fases en orden (1 → 5).

Si compartes la plantilla del formulario o capturas de pantalla del PDF, puedo proponer un mapeo concreto de campos y el diseño de la tabla de verificación.
