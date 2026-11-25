# Cambio: proyección backend del menú web (#2785, F1b)

## Alcance

Se añade `src/backends/sisoc_core/usuarios/web_navigation.py`, con
`build_web_navigation(request)`, y su prueba pública
`src/backends/sisoc_core/tests/test_web_navigation.py`.
Es una unidad interna del piloto original de INS-A, conservada al separar el
trabajo local actual: no publica el contexto de sesión ni modifica la navegación
de producción.

## Comportamiento

La proyección devuelve elementos JSON con `id`, `label`, `href` y `children`.
Conserva jerarquía, etiquetas, enlaces internos y orden visual del menú Django,
incluido el orden CSS de grupos, grupos visibles sin hijos y Mi cuenta al final.
No transporta HTML, objetos de usuario ni listas completas de permisos.

Reutiliza filtros de permisos/IAM, predicados registrados por los dominios y el
proveedor de tableros. No importa verticales, instala dependencias ni agrega un
registro paralelo. La duplicación temporal se limita a condiciones de presentación;
las acciones siguen necesitando su propia autorización en backend. El futuro
contexto llamará a esta proyección solamente después de evaluar requisitos web.

Los tableros conservan la jerarquía y orden del proveedor, no su indicador activo
calculado para la URL de la API. El cliente resolverá el estado activo para la
página lógica. Un proveedor ausente conserva el resultado vacío existente; un
error real se propaga, sin convertirlo en contexto listo. Los enlaces proyectados
de tableros se limitan a paths internos conforme al contrato propuesto.

Los bloques `False` y los comentarios Django permanecen deshabilitados. La
comparación real detectó y corrigió un enlace comentado de Rendición Final y la
etiqueta PAS: no se reactivó el enlace ni se modificó la política RF1. También se
confirmó que las dos iniciales del avatar estaban comentadas, no vigentes; el
contrato de inicial del username no cambia.

## Verificación

- Primer intento de tests bloqueado por indisponibilidad transitoria del engine
  Docker. El borrador inicial fue escrito antes de observar RED; se registra esta
  excepción de runner, sin afirmar un ciclo test-first que no ocurrió.
- Tras recuperar el runner se corrigió la fixture que duplicaba el Profile creado
  por signal. Eso fue un defecto de la prueba, no de producción.
- RED funcional observado: la proyección del superusuario no coincidía con el
  template renderizado, por el enlace comentado y la etiqueta PAS. Se corrigieron
  ambas diferencias y se conservó el test de regresión.
- GREEN: 32 pruebas, cobertura del módulo 98,4%. Comparación de jerarquía, enlaces,
  etiquetas y orden contra el template renderizado con usuarios sintéticos:
  permisos por dominio, superusuario, restricciones VAT/CDI/DataCalle, precedencia
  and/or, grupo CFPINET y tableros agrupados/ausentes/fallidos.
- Regresión: 36 pruebas existentes de menú, grupos, VAT, tableros/footer y requisitos
  de sesión aprobadas. Black check conforme; Pylint 10/10.
- Misma imagen local y aislamiento de F1a: sin red, repositorio readonly, `env -i`,
  dotenv deshabilitado, SQLite de tests y logs/media/cache/coverage en tmpfs. No se
  arrancaron servidores, accedieron datos reales ni realizaron conexiones externas.
- La verificación independiente detectó un bloqueo real: INET se había anidado
  por error dentro del guard que oculta otras secciones a usuarios exclusivos de
  VAT. Se movió la comprobación VAT fuera de ese guard, como el template legado,
  y se añadió una regresión con usuario ordinario. Recheck acotado: dos pruebas
  aprobadas, incluido el probe original. Sin bloqueantes pendientes.
- Advisory: algunos IDs de grupos coinciden con IDs de sus hijos; son estables y
  la jerarquía los distingue. No se promete unicidad global ni se cambia el
  contrato por una condición no solicitada. El renderer debe distinguirlos por
  su posición/ancestros, no por un mapa global que colapse elementos.

## Limitaciones y retorno

La comparación de HTML renderizado es funcional/estructural, no un diff de píxeles.
No se entregaron todavía endpoint HTTP, shell React, archivos de referencia visual
ni aceptación humana. No hay CI, publicación, activación ni deploy de esta unidad.
Los archivos nuevos no tienen consumidores de producción; su retiro no requiere
revertir datos, permisos, providers o middleware existentes.

Riesgo: item 2, proyección de visibilidad basada en permisos. Requiere revisión
técnica; el resultado de menú no sustituye autorización de acciones.
