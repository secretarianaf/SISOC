# Mapa de arquitectura: servicios y frontends

## Resultado acordado

Mostrar en `/arquitectura/` los backends independientes, sus apps y prefijos
del proxy, el core de entrada, el kernel compartido y los frontends React.
Conservar el mapa de módulos, imports, menú y PWA, leyendo los registros
existentes sin mantener otro inventario manual.

## Implementación

- El generador lee `src/backends/config/backends.json`, ubica el dueño de cada
  app y descubre los paquetes de `src/frontends/apps/`. Las claves de
  `FRONTEND_V2_UPSTREAMS` permiten distinguir workspaces sin proxy y proxies
  sin workspace. No se ejecutan settings ni se incluyen valores de entorno,
  direcciones internas o credenciales.
- El visor agrega nodos y una capa de relaciones de servicios: apps propias,
  kernel compartido y reenvío desde el core a backends y frontends. La
  asociación frontend/backend por identificador se etiqueta como inferida y
  se dibuja punteada: no demuestra qué endpoints consume el cliente.
- La imagen del core no incluye código de otros verticales ni frontends.
  Por eso la etapa `source` captura el grafo completo con `--imagen` antes de
  recortar el código. El comando del arranque recupera esa captura y escribe
  atómicamente el grafo de runtime. Conserva la fecha de captura y la fuente
  `imagen`. Si el checkout tiene todos los backends y los workspaces, vuelve
  a leer el código aunque exista una captura previa de `--imagen`.
- Un registro de backends mal formado hace fallar la generación; el arranque
  del servidor mantiene su comportamiento de continuar si falla el mapa.
- Los artefactos de `docs/arquitectura/` se actualizan con `--docs`, no en el
  arranque. El grafo de runtime sigue protegido por sesión y fuera de `/static/`.

## Alcance y límites

El mapa representa el código de una imagen o checkout, no el inventario vivo
de un entorno. Un deploy selectivo puede dejar versiones distintas entre
servicios; el mapa no confirma esa sincronización ni la disponibilidad real.
No cambian endpoints, permisos, datos, esquemas ni dependencias.

## Validación

Pruebas del generador sin DB: propietarios y prefijos del registro, detección
de frontends nuevos, workspace/proxy faltantes, registro inválido, exclusión
de metadatos sensibles y conservación de la captura al arrancar sin código
de verticales. Se comprueba además el orden de captura en el Dockerfile.
Resultado local: 18 pruebas pasaron, sin cargar Django ni usar DB. Pasaron
Black, djlint del template, sintaxis de JavaScript, chequeo local de errores de Pylint sin plugins,
el verificador de rutas documentadas (81 documentos, 0 referencias obsoletas)
y `git diff --check`. En Chromium local se verificaron inventario, selección,
detalle, búsqueda, cambio de capa, etiqueta de inferencia y ancho de 390 px
sin desborde horizontal. Esta prueba usa el HTML documental, no la sesión Django.
Pylint completo con Django y pylint_django se ejecutó desde la caché local de
uv con Pylint 3, compatible con la configuración del repo: no pasa limpio
por advertencias de longitud del módulo, complejidad y una variable existente
con caracteres no ASCII. El aumento de longitud supera ahora el umbral de
1000 líneas; queda explícito sin ampliar el alcance a una refactorización.
El chequeo de errores de Pylint sin plugins pasó. Las herramientas se
ejecutaron desde cachés locales, sin dependencias nuevas en el proyecto.
La construcción real de imágenes y la navegación autenticada en un entorno
desplegado quedan pendientes de validación operativa autorizada.

Comandos pendientes, solo en un entorno local aislado y autorizado:

```bash
docker build --target core -f docker/django/Dockerfile .
docker compose exec django pytest src/backends/kernel/tests/test_mapa_arquitectura_smoke.py -v
```
