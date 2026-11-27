# Cambio: nombres con referencias HTML guardadas como texto (#2927)

## Alcance

En Historia Social Digital había legajos cuyo apellido se leía `Mu&#327;Oz`. No es un problema de pantalla: el valor está guardado así en la base, con una referencia numérica HTML (`&#NNN;`) en lugar de la letra. El listado y el legajo muestran lo que hay guardado.

## Comportamiento

`repair_utf8_mojibake` en `src/backends/kernel/core/services/text_encoding.py` ahora también decodifica referencias numéricas (decimales y hexadecimales) cuando representan una letra, una marca o uno de estos signos: `'`, `’`, `´`, `°`. No toca entidades con nombre (`&ntilde;`) ni referencias a símbolos como `<`, `>` o `&`, así el resultado nunca agrega marcado HTML. Si `title()` había partido la palabra en la referencia (`Mu&#241;Oz`), normaliza solo ese token (`Muñoz`).

Como la función ya se usaba en esos puntos, el cambio alcanza a:

- la respuesta de RENAPER (`src/backends/kernel/core/integrations/renaper.py`): los datos nuevos se guardan ya decodificados;
- el comando `repair_utf8_mojibake`, que corrige nombres y apellidos existentes de ciudadanos y nóminas CDI;
- el comando `audit_utf8_mojibake` y la comparación de nombres contra RENAPER.

## Datos existentes

Desplegar el cambio no corrige los legajos ya guardados. Hace falta correr el comando, con el mismo runbook de `docs/registro/cambios/2026-T3/2026-09-01-reparacion-mojibake-datos.md` (dry-run primero; `--apply` con backup, ventana y autorización operativa):

```bash
python manage.py repair_utf8_mojibake --target ciudadano
python manage.py repair_utf8_mojibake --target ciudadano --apply
```

## Verificación

`src/backends/kernel/tests/test_text_encoding.py` cubre la decodificación, la idempotencia y los casos que no se tocan; `src/backends/kernel/tests/test_consulta_renaper_unit.py` cubre el payload de RENAPER y `src/backends/cdi/tests/test_repair_utf8_mojibake_command.py` la reparación de un ciudadano.

## Limitaciones

- El legajo del issue tiene `&#327;`, que es `Ň` (N con carón) y no `Ñ` (`&#209;`). Tras la reparación se lee `Muňoz`, no `Muñoz`. No se reemplaza `Ň` por `Ñ` porque sería adivinar el dato; si se confirma que siempre es un error del origen, es una corrección de datos aparte.
- No se identificó qué carga generó ese valor; solo se confirmó por la captura que está guardado así.
- No se probó en navegador ni contra los datos de homologación.
