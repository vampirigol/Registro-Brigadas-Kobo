# Comparativa: PDF (formulario brigadas) vs Formulario web KoboToolbox

## Mapeo de campos principales

| Campo en PDF | Path en formulario web | Grupo web | Notas |
|--------------|------------------------|-----------|-------|
| Nombre | `group_py4vt65/NAME` | Información Personal | Nombre del paciente |
| Edad | `group_py4vt65/AGE` | Información Personal | number |
| Fecha consulta | `Fecha_de_atenci_n` | Raíz | Formato DD/MM/AA |
| Sexo M/H | `group_py4vt65/SEX` | Información Personal | M o H |
| Fecha nacimiento | `group_py4vt65/DOB` | Información Personal | DD/MM/AA |
| Nacionalidad | `group_py4vt65/NAT` | Información Personal | select-one |
| Estado | `group_py4vt65/Estado` | Información Personal | select-one |
| Estatura | `group_jt9yr10/HEI` | Toma de medidas | Talla (cm) |
| Peso | `group_jt9yr10/WEI` | Toma de medidas | Peso (kg) |
| Estatus migratorio | `group_py4vt65/estatus_migra` | Información Personal | radio |
| Mujer embarazada/Lactancia | `group_py4vt65/ME_ML` | Información Personal | radio |
| Minoría étnica | `group_py4vt65/_Pertenece_a_alguna_minor_a_t` | Información Personal | radio SI/NO |
| Especificar minoría | `group_py4vt65/Especificar_Minor_a_tnica` | Información Personal | text |
| Primera vez/Seguimiento | `group_ua6kz91/followup` | Primera vez o Seguimiento | radio |
| Motivo consulta | `group_jt9yr10/HPI` | Toma de medidas | Padecimiento médico actual |
| Diagnóstico | `group_rd6ms59/DX` o `group_oc2gd73/Diagn_stico_001` etc | Por especialidad | select-multiple o checkbox |
| Referencia paciente | `group_xi7cn52/REF` | Referencias | radio |
| Servicio que se brinda | `group_ua6kz91/Servicio_que_se_brinda` | Primera vez o Seguimiento | DENTAL, MEDGEN, OFTALMO, LAB, etc. |
| ¿Asesoría módulos hoy? | `group_ua6kz91/ASESPREV` | Primera vez o Seguimiento | **select-multiple: TODOS los servicios** |
| Entrega tratamiento | `group_ic1bl54/entrega_tx` | Tratamiento | radio |
| Unidades entregadas | `group_ic1bl54/Unidades_entregadas` | Tratamiento | number |
| Plan de tratamiento | `group_ic1bl54/Plan_de_Tratamiento` | Tratamiento | text |
| ¿Requiere anteojos? | `group_ic1bl54/_Requiere_anteojos` | Tratamiento | radio |
| Procedimiento odontológico | `group_ic1bl54/_Se_realiza_procedimiento_odon` | Tratamiento | radio |
| Lugar atención | `group_nl0pw33/BCS`, `CHIH`, `Lugar_de_Atenci_n_Sonora`, etc. | Lugar de atención | radio según estado |
| PLACE (colegio/comunidad) | `group_nl0pw33/PLACE` | Lugar de atención | text |

## Servicio que se brinda (por especialidad)

El campo `Servicio_que_se_brinda` (radio) y `ASESPREV` (select-multiple) deben reflejar la especialidad/servicio del registro actual. Valores típicos en el formulario web:
- Medicina General
- Odontología
- Oftalmología
- Fisioterapia
- Laboratorio
- Entrega de insumos

## Grupos del formulario web por especialidad

| Especialidad PDF | Grupos web que aplicar |
|------------------|------------------------|
| ODONTOLOGÍA | group_oc2gd73 (Diagnóstico), group_ic1bl54 (Tratamiento, procedimiento) |
| MEDICINA GENERAL | group_rd6ms59 (DX, discapacidad), group_ic1bl54 (tratamiento) |
| OFTALMOLOGÍA | group_rw8yu96 (síntomas, diagnóstico), group_ic1bl54 (anteojos) |
| FISIOTERAPIA | group_mi31k30 (Diagnóstico, localización) |
| LABORATORIO | Campos específicos de laboratorio |
| ENTREGA INSUMOS | group_ic1bl54 (entrega_tx, Especifique_qu_se_entrega) |
