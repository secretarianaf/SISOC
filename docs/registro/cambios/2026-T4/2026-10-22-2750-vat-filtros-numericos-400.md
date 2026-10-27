# Cambio: la API de VAT responde 400 ante filtros numéricos inválidos (#2750, punto 3)

## Alcance

`GET /api/vat/comisiones-curso/` respondió 500 unas 522 veces en PRD entre el
16/10 y el 21/10 con `ValueError: Field 'id' expected a number but got
'26-1912-14'`. Un consumidor con API key manda en `curso_id` un código
compuesto `N-N-N`, que llegaba sin validar al ORM. El mismo riesgo existía en
todos los filtros `*_id` de la API de VAT.

Se agregó `query_param_entero` en `src/backends/vat/VAT/api_views.py`, junto a
`normalizar_cue_consulta`, la validación que ya existía. Se usa en los 47
filtros numéricos de `src/backends/vat/VAT/api_views.py` y
`src/backends/vat/VAT/api_web_views.py`: todos los `*_id` y `ciclo_lectivo`.

## Comportamiento

- Un valor que no es entero, como `?curso_id=26-1912-14`, responde 400 con
  `{"curso_id": ["Debe ser un número entero."]}` en vez de 500.
- Un valor vacío se ignora, igual que antes. Un id válido filtra igual que antes.
- No se reinterpreta el código `N-N-N` como otro filtro. No se pudo identificar
  qué cliente lo manda: no está en el repo, el log de Django no registra quién
  llama y en `prd-old` no hay un proxy con access log. Queda pendiente avisar al
  consumidor de la API key.

## Verificación

- `test_api_vat_filtro_numerico_invalido_responde_400` en
  `src/backends/vat/VAT/tests.py`, parametrizado con los 47 pares
  endpoint/parámetro, y `test_api_vat_filtro_numerico_vacio_se_ignora`. Sin el
  fix, el caso `comisiones-curso` + `curso_id` falla con el mismo `ValueError`
  de PRD.
- `pytest src/backends/vat/ -n auto`: 474 passed, 3 skipped.
- black y pylint (10/10) de los archivos tocados.
