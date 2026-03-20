# Especificación ETL: PDF → Tabla Normalizada → KoboToolbox

## Objetivo

Automatizar la carga de formularios PDF escaneados (manuscritos) siguiendo un flujo ETL que replica la lógica de "Reorganización de Datos por Especialidad.xlsx".

---

## Estructura de Salida Esperada (según Excel)

| Columna | Descripción | Origen |
|---------|-------------|--------|
| Nombre del Paciente | Datos estáticos del paciente | Cabecera PDF |
| Fecha | Fecha de atención | Cabecera PDF |
| Sexo | F/H | Cabecera PDF |
| Servicio Brindado | Odontología, Laboratorio, Oftalmología, Fisioterapia, Medicina General | Tabla especialidades (qué filas tienen X) |
| Diagnóstico / Motivo | Específico por especialidad | Celda correspondiente a esa especialidad |
| Talla / Peso | Mismo en todas las filas del paciente | Cabecera (ej. 1.67 / 63) |
| Resultados Lab / Insumos | Específico por especialidad | Lab: G:C:T:H; Dental: Kit, Limpieza; Oftalmo: Lentes, Medicamentos; etc. |

**Regla 1:N:** 1 paciente con 4 especialidades marcadas → 4 filas (una por especialidad).

---

## Fases del Flujo ETL

### 1. Ingesta y Esquema (Formulario Maestro)

- **Input:** PDF maestro o definición de campos.
- **Output:** Esquema de campos clave:
  - Cabecera: Nombre, Fecha nacimiento, Edad, Sexo, Estatura, Peso, Estatus migratorio, etc.
  - Tabla especialidades: filas ODONTOLOGÍA, FISIOTERAPIA, MEDICINA GENERAL, OFTALMOLOGÍA, LABORATORIO CLÍNICO.
  - Por especialidad: servicios (CONSULTA, LIMPIEZA, EXTRACCIÓN, MEDICAMENTOS, GLUCOSA, etc.) y si tienen cantidad.

### 2. Extracción (OCR)

- **Input:** PDF escaneado (ej. Ligui 17-02-26).
- **Proceso:**
  - OCR por página (Tesseract).
  - Extracción de metadatos de cabecera (regex/patrones).
  - Detección de X en la tabla de especialidades (por bloque de texto).
  - Por cada especialidad marcada: extraer diagnóstico y resultados específicos de esa fila.

- **Desafío:** En manuscritos, OCR puede fallar. Se requiere etapa de verificación humana.

### 3. Transformación (1:N + Asignación por Especialidad)

```
Para cada paciente P extraído:
  especialidades_marcadas = [Esp1, Esp2, ...]
  Para cada Esp en especialidades_marcadas:
    Crear fila F
    F.Nombre = P.Nombre
    F.Fecha = P.Fecha
    F.Sexo = P.Sexo
    F.Talla = P.Estatura
    F.Peso = P.Peso
    F.Servicio_Brindado = Esp
    F.Diagnostico = datos_extraidos[Esp].diagnostico  // específico
    F.Resultados_Lab_Insumos = datos_extraidos[Esp].resultados  // específico
    Agregar F a tabla_salida
```

**Asignación por especialidad:**

| Especialidad | Diagnóstico/Motivo | Resultados/Insumos |
|--------------|-------------------|--------------------|
| Odontología | Limpieza, Caries, Consulta, Cálculo | Kit limpieza dental, Consulta marcada |
| Fisioterapia | Lesión espalda, Dental, Lumbalgia | Paracetamol, Tratamiento 1/2 |
| Medicina General | Consulta, Gripe, Otitis | Medicamentos, 3 Medicamentos |
| Oftalmología | Presbicia, Consulta | Lentes, Medicamentos |
| Laboratorio | Control, Glucosa, Hiperlipidemia | G:111, C:180, T:167, H:51 |

### 4. Carga (Tabla + KoboToolbox)

- Exportar a Excel/CSV en el formato del Excel de referencia.
- Opcional: verificación humana en tabla editable.
- Envío a KoboToolbox (formulario web) fila por fila.

---

## Mapeo Tabla ETL → Formulario KoboToolbox

| Columna ETL | Campo Kobo (path) |
|-------------|-------------------|
| Nombre del Paciente | group_py4vt65/NAME |
| Fecha | Fecha_de_atenci_n |
| Sexo (F/H) | group_py4vt65/SEX |
| Talla | group_jt9yr10/HEI |
| Peso | group_jt9yr10/WEI |
| Servicio Brindado | group_ua6kz91/Servicio_que_se_brinda |
| Diagnóstico/Motivo | group_rd6ms59/dxesp, group_oc2gd73/Especificar_002, etc. (por especialidad) |
| Resultados Lab/Insumos | group_ic1bl54/Especificar_lo_que_se_entrega_, Unidades_entregadas, etc. |

---

## Implementación Propuesta

1. **Parser por especialidad:** Para cada especialidad con X, extraer el bloque de texto de esa fila y buscar diagnóstico y resultados (regex adaptados).
2. **Estructura de datos intermedia:** `{ paciente: {...}, especialidades: [{ nombre, diagnostico, resultados }] }`.
3. **Generación de filas:** Bucle 1:N como arriba.
4. **Tabla de verificación:** Mostrar filas generadas; usuario edita y confirma.
5. **Carga a Kobo:** Usar el flujo actual (Excel → form filler).
