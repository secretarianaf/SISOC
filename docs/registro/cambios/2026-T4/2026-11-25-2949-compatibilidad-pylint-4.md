# Cambio: compatibilidad del linter con Pylint 4 (#2949)

## Alcance

Actualizar Pylint requiere alinear el pin de Astroid y quitar
`suggestion-mode`, que se eliminó en Pylint 4. Se mantienen el comando y
su umbral de CI.

## Comportamiento

No cambia el runtime. Las excepciones son locales a nombres públicos de Django,
registros internos reasignados, firmas existentes y dos inferencias falsas de
`FileField.clean`. No se desactiva ningún diagnóstico de forma global.

## Verificación

Se comparó el AST antes y después en los ocho archivos Python y se comprobó
que `FileField.clean(self, data, initial)` existe en Django. No cambia el
esquema ni se modifica un workflow.

Referencia: [Cambios incompatibles de Pylint 4.0](https://pylint.readthedocs.io/en/latest/whatsnew/4/4.0/index.html#breaking-changes).
