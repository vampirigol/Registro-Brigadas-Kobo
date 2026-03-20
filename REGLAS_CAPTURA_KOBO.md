# Reglas de captura para KoboToolbox (según ejemplo ADRA)

## Fuente
Ejemplo de captura de información - Fernanda (ADRA) - Cómo realizar el registro de servicios en Kobo.

---

## Regla principal: 1 registro = 1 formulario por especialidad/fecha

Cada vez que un paciente recibe atención en una **especialidad o servicio**, se hace **un registro completo** (un formulario web llenado).

### Ejemplo Keila (24 y 28 febrero)

- **24 feb:** Pasa a DENTAL, MedGen, OFTALMO → **3 registros** (uno por cada uno)
  - REG #1: MEDGEN (diagnósticos, medicamentos, plan de tratamiento)
  - REG #2: DENTAL (diagnósticos, procedimientos, insumos)
  - REG #3: OFTALMO (necesita anteojos, entrega el 28)

- **28 feb:** Pasa a Entrega de insumos + Laboratorio → **2 registros**
  - REG #1: ENTREGA DE INSUMOS (recibe anteojos)
  - REG #2: LABORATORIO (formulario completo + reporte de laboratorio)

**Total: 5 registros = 5 formularios llenados**

---

## Regla práctica (nota manuscrita)

> "En la práctica todo ocurre en la misma fecha, así que el insumo va en el mismo registro de Oftalmo."

Cuando la entrega de insumos ocurre el **mismo día** que la consulta de una especialidad, se registra **junto con esa especialidad**, no como registro aparte.

---

## Contenido por registro

| Especialidad/Servicio | Qué registrar |
|----------------------|----------------|
| **MEDGEN** (Medicina General) | Diagnósticos aplicables, medicamentos recibidos, plan de tratamiento |
| **DENTAL** (Odontología) | Diagnósticos, procedimientos realizados, entrega de insumos |
| **OFTALMO** (Oftalmología) | Diagnósticos, si necesita anteojos, si hubo entrega o fecha de entrega |
| **ENTREGA DE INSUMOS** | Qué insumos recibe (anteojos, kits, etc.) |
| **LAB** (Laboratorio) | Formulario completo + registro de reporte de laboratorio |

---

## Campo específico del formulario

**"¿Se le ha brindado asesoría en uno de los módulos el día de hoy?"**

→ Se seleccionan **TODOS** los servicios a los que pasó el paciente ese día.

---

## Resumen para la automatización

1. Por cada paciente en el PDF: detectar especialidades/servicios con (x) marcado.
2. Generar N registros = N especialidades marcadas (o N servicios distintos si hay entrega de insumos separada).
3. Cada registro incluye: datos demográficos + datos de consulta + datos específicos de esa especialidad.
4. Si el PDF indica fecha única: aplicar regla práctica (insumos junto a la especialidad).
5. Campo "asesoría/módulos": marcar todos los servicios que el paciente recibió ese día.
