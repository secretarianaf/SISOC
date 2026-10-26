# Cambio: ubicación de Dispositivos (#2777)

## Alcance

Se agrega localidad del catálogo territorial y coordenadas explícitas al formulario
existente de Dispositivos. Se incorpora mapa en el legajo y previsualización en
alta y edición, siguiendo el patrón de `ver_para_ser_libre/sede_form.html`.
El domicilio mantiene provincia, municipio, calle y altura ya existentes.

Código en `src/backends/dispositivos/dispositivos/`: modelo, formulario, servicios,
vistas, templates y estáticos propios del vertical.

## Comportamiento

- Localidad opcional, filtrada por municipio y validada en servidor. No se
  infieren localidades para registros existentes.
- Latitud y longitud opcionales como par, con seis decimales y límites
  geográficos (-90/90 y -180/180). El cero es una coordenada válida.
- El mapa del legajo y la previsualización priorizan coordenadas explícitas;
  si faltan ambas usan domicilio, localidad (si existe), municipio y provincia.
- La previsualización no persiste cambios. El guardado usa los permisos y alcance
  territorial existentes; el domicilio textual no se modifica por coordenadas.
- El mapa general y su endpoint de ubicación priorizan las coordenadas cargadas,
  sin consultar Georef en ese caso. Sin coordenadas conservan la búsqueda y caché
  por dirección; incorporar o cambiar localidad invalida ese resultado.
- Se conservan resultados Georef anteriores para domicilios sin localidad.
- No incluye arrastre del pin: corresponde al trabajo transversal del #2778.

## Migración y riesgo

La migración `0007_dispositivo_latitud_dispositivo_localidad_and_more.py` agrega
columnas anulables, sin transformar ni borrar domicilios. Requiere revisión técnica.
Debe aplicarse antes de ejecutar el código actualizado, con el migrador habitual.
No agrega dependencias, modelos, settings ni permisos nuevos.

## Verificación

- Suite Python de Dispositivos: 84 tests pasaron; cobertura de la app del 94% en
  la primera ejecución. Cubre guardado, domicilio conservado, localidad ajena,
  coordenadas inválidas, prioridad de coordenadas y edición sin permisos.
- Tests Node de mapas de Dispositivos: 19 pasaron, incluidos previsualización,
  coordenadas parciales, cero y respuestas territoriales desactualizadas.
- Black: 8 archivos sin cambios pendientes. Pylint de los cuatro archivos de
  aplicación modificados: 10/10. Djlint: tres templates sin errores de lint.
- Migración aplicada en MySQL local; `makemigrations --check --dry-run` sin
  cambios pendientes. SISOC responde HTTP 200 en `http://localhost:8002/`. Se
  usaron puertos alternativos 8002/3308 para evitar otras aplicaciones locales.
- Verificación visual confirmada por quien pidió en el entorno local: campos y
  mapa visibles; bloque Ubicación con calle y altura primero, luego provincia,
  municipio, localidad, coordenadas y mapa; contacto y responsable aparte.
- Caso inválido manual confirmado: latitud 91 y longitud 0 en Previsualizar
  muestran el aviso de coordenadas inválidas y conservan el mapa anterior.
- Persistencia y permisos verificados mediante tests automáticos; no se afirma
  una prueba manual de guardado.
- CI: pendiente de publicación del PR. Sin merge ni despliegue.
