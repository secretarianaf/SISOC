# #2641: revisión previa a la publicación

El responsable pidió commitear sistemáticamente y crear un PR documentado con
diagrama. Esta autorización reemplaza el límite anterior de stage/commit/push
para publicar la rama y el PR. Se conservan las restricciones de merge, cierre
del issue, deploy y entornos existentes. Los registros anteriores describen su
momento de ejecución; no se reescriben como si entonces hubiera publicación.

## Organización y preservación

Se reconstruyeron ocho árboles de commits a partir de los ZIP y manifiestos
SHA256 de C0–C1, C2, C3, C4, fixtures, dependencias, build y smoke. Los índices
temporales no restauraron archivos sobre el workspace. El último árbol coincide
con el resultado de `git add` del estado final validado: 1910 entradas en el
manifiesto, incluyendo borrados y archivos sin rastrear de los movimientos.
Los commits se generan ahora, sin atribuirles fechas históricas de ejecución.

## Revisión y corrección

Se aplicó `code-review` con ejes separados, contra la base
`1cede84d2b3490f2ddb6bf933852408d9fd68bc7` y las decisiones aprobadas.
Estándares: cero hallazgos accionables en revisión estática focalizada.
Especificación: un P2 sobre revocación de controles del ABM independiente.
La revisión no fue exhaustiva de cada recurso trasladado ni una prueba runtime.

Un checkbox desmarcado o un select múltiple vacío no envía su nombre en HTML.
`IdentityAdminForm` preservaba todo campo omitido en edición, por lo que un
guardado exitoso podía conservar acceso web/SIIS o el último grupo/permiso.
Se agrega `_identity_present` junto a diez controles genéricos habilitados;
el normalizador convierte sólo esos vaciados en valores explícitos antes de
clasificar la operación y validar el formulario. Omitir un campo sin marcador
sigue conservándolo. El marcador no concede permisos ni evita al dueño.

Se preserva la validación de efectos de grupos/permisos de Comedores y la
restricción por sección del actor. Los controles deshabilitados no emiten
marcador: evita derivar falsamente al dueño una autoedición provincial. La
revisión de ese delta cerró ambos bordes sin nuevos hallazgos concretos.

Archivos: `users/admin_operations.py`, `users/admin_forms.py`, template compartido
`user/user_form.html` y tests `test_issue_2641_identidad_disponible.py` en sus
dueños actuales. La corrección queda en un commit propio posterior a los ocho
snapshots. Su reversa pierde la corrección de vaciado; no cambia schema ni datos.

## Evidencia nueva y límites

- Regresión inicial: **6 failed, 1 passed**. Los fallos reproducen cuatro vaciados,
  la clasificación de una revocación dependiente y los marcadores HTML ausentes.
- Primera pasada tras el cambio: 32 passed, 1 failed por usar en el test un grupo
  arbitrario que el clasificador trata conservadoramente como dependiente.
  Se usó el grupo independiente conocido `Usuario Ver`; no se relajó producción.
- Final: **34 passed**, seis deprecaciones existentes, 17.65 s, en SQLite dentro
  de la imagen dev nueva, con fuentes montadas y sin red. Incluye omisiones,
  rechazos, permisos, concurrencia ya cubierta por el módulo y autoedición.
- Black de tres Python, Pylint **10/10**, djlint del template con la configuración
  del repositorio y `git diff --check`. Logs `publish-2641-*` en el scratch local.

Los ensayos de imágenes/HTTP anteriores preceden esta corrección; no se afirma
que esas imágenes contengan el nuevo fix. CI debe reconstruir el HEAD publicado.
No se repitió MySQL para este delta ni la suite integral. No hay aceptación
humana, deploy o prueba nueva de workers productivos por publicar el PR.

La guía `docs/desarrollo/arquitectura_servicios_2641.md` y el SVG versionado
explican la topología final, recorrido de lectura, alcance y reversa. El SVG se
parseó como XML y se renderizó para inspección visual. La fuente Mermaid queda
en la guía y el PR para lectura directa en GitHub.
