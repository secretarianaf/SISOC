# Hotfix #2908: asignación de Coordinador DataCalle

## Problema y decisión

El formulario de Comedores asignaba el grupo seleccionado y luego lo quitaba
al sincronizarlo con un rol DataCalle vacío. El formulario de identidad podía
conservar el grupo sin rol ni alcance, una combinación potencialmente nacional.
El usuario confirmó que el grupo debe guardarse junto al rol coordinador y
exigir una provincia, mostrando un error si falta.

## Implementación

`RelevadorCalleFormMixin` reconcilia una selección nueva del grupo antes de la
validación habitual. Reutiliza las restricciones de actor, rol y alcance. El
formulario de identidad incluye los valores derivados entre los campos que
debe persistir, aunque los controles no hayan viajado en el POST.
La falta de provincia se informa también junto a grupos, fuera del panel oculto.
No cambia el sincronizador simétrico de grupos ni modifica datos existentes.

## Verificación

Regresión en `src/backends/dispositivos/tests/test_issue_2908_datacalle_group.py`:
alta y edición en ambos formularios, provincia obligatoria y única, rechazo de
delegación sin autoridad y ausencia de escrituras al rechazar el formulario.
Se observó RED antes del cambio: los diez casos fallaban.

Suite relacionada: `test_datacalle_roles.py` y `test_users_secciones_por_permiso.py`.
Entorno aislado: contenedor nuevo, red deshabilitada, SQLite sintético, código
montado sólo lectura; sin acceso a bases reales. Resultado final: 65 pruebas
aprobadas, incluyendo regresiones y suites relacionadas. Black aplicado.

La verificación independiente no encontró defectos atribuibles al cambio.
Probó además conflictos de alcance, autoridad insuficiente aun con sección y
grupo delegados, y revocación/degradación con el grupo reenviado. Dos probes de
revocación/degradación directa por identidad fueron rechazados por el guard
preexistente que exige pasar por Espacios comunitarios; el mismo rechazo se
reprodujo en el commit base. Los probes aplicables se incorporaron como tests.

Pendientes: CI remota y recorrido integrado de navegador. La prueba local
ejercita formularios reales y persistencia, no demuestra aceptación visual ni
el reenvío HTTP entre servicios de un entorno desplegado.

## Límites y reversión

No incluye migraciones ni reparación de perfiles históricos. No agrega roles
ni amplía quién puede asignarlos. Revertir el commit del hotfix revierte la
reconciliación y sus pruebas; no hay cambio de esquema que revertir.

Risk: item 2 (asignación de permisos y alcance territorial).
