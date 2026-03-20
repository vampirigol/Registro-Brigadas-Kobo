# Reglas de llenado automático – Formulario web KoboToolbox

Adaptado a la plantilla **Plantilla_Brigadas_Salud_Clinicas** y a la lógica de relevancia del formulario.

---

## Dependencias del formulario (importante)

### 1. Toma de consentimiento antes de iniciar la consulta (CONS1)

- **Si no se selecciona "Sí"**, el formulario **no muestra** el campo **Nombre del paciente\***.
- Por eso el llenado automático **siempre marca CONS1 = Sí** al inicio, antes de rellenar el resto.
- Así la casilla de nombre aparece y se puede completar.

### 2. Nacionalidad (NAT) y Estado

- **Si nacionalidad no es "México"**, el formulario **no muestra** el campo **Estado** (origen de la persona).
- Para brigadas en México, en las reglas de llenado se usa **NAT = México** por defecto.
- El orden en el mapeo hace que se rellene **NAT antes que Estado**; tras NAT se espera un momento para que Enketo muestre Estado.

### 3. Nombre del paciente

- Según la plantilla: *"Escribir el nombre completo en mayúsculas, exactamente como aparece en identificación oficial. Si el paciente no autoriza proporcionar esta información, registre 'NA'."*
- El llenado automático convierte el nombre a **mayúsculas**.
- Si en el Excel viene "NA" o "na", se envía **"NA"**.

---

## Columnas Excel (Plantilla_Brigadas_Salud_Clinicas)

El loader reconoce, entre otras:

| Columna en Excel (con o sin *) | Campo interno |
|--------------------------------|----------------|
| Nombre del Paciente / Nombre del Paciente* | NAME |
| Fecha de atención* | Fecha_de_atenci_n |
| Toma consentimiento inicial | CONS1 |
| Nacionalidad | NAT |
| Estado* | Estado_brigada |
| Lugar de atención | Lugar |
| Modalidad de la atención | Modalidad_de_atenci_n |
| Servicio que se brinda | Servicio_que_se_brinda |
| Edad, Sexo, Fecha de nacimiento | AGE, SEX, DOB |
| Talla (cm), Peso (kg) | HEI, WEI |
| Padecimiento médico actual / Motivo de la consulta | Diagnostico_Motivo |
| Entrega de tratamiento / Insumos | entrega_tx, Resultados_Lab_Insumos |
| ¿Se hizo referencia? | Referencia |
| Estatus migratorio | estatus_migra |

Los encabezados con asterisco (`*`) se normalizan (se quita el `*`) para buscar el mapeo.

---

## Orden de llenado en pantalla

1. **Consentimiento (CONS1) = Sí** → se muestra Nombre del paciente.
2. Resto de campos en el orden del `mapping.yaml` (página por página).
3. **NAT = México** se rellena antes que **Estado** para que el campo Estado aparezca.

Si subes el Excel **Plantilla_Brigadas_Salud_Clinicas.xlsx**, verifica que los nombres de columna coincidan con la tabla anterior (con o sin `*` en obligatorios).
