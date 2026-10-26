# Guía de trabajo de verticales independientes (#2638)

Se contrastó el issue con el checkout que integra #2646 y con el tracker.
La guía nueva `docs/desarrollo/verticales_independientes.md` explica dueños,
contratos, controles reales y sus límites, cuatro checklists, diagrama Mermaid,
deploy y diagnóstico. Los resúmenes de agentes remiten a esa guía;
MODULAR_BOUNDARIES deja de presentar la separación como trabajo futuro.

Se actualizaron rutas de documentos vigentes y referencias que cambiaron de
dueño (gestión de organizaciones, usuarios y accesos PWA); las migraciones
históricas squashed de users remiten al archivo actual. Los registros y
snapshots conservan rutas de su época. La guía operativa refleja collectstatic
en migrador y API de Celiaquía, y matiza el selector de tests/frontend.

`src/scripts/ci/check_docs_paths.py` comprueba literales de raíces movidas con
stdlib y alcance documentado; no incorpora dependencias, cambios de CI ni
reglas nuevas de arquitectura. Se prefirieron los checklists compartidos a
crear otra skill obligatoria.

Análisis, plan, evidencia de recorridos y límites de validación:
`docs/plans/2026-T4/2026-10-05-issue-2638-documentacion-verticales.md`.
Veinte tests existentes del selector y ocho simulaciones pasaron; la
validación de documentación no demuestra despliegue, conservación de datos
ni aceptación humana. El nuevo script hace que el selector clasifique el
conjunto completo como deploy completo; no se modifica el selector ni se
despliega como parte de este trabajo.

Continuación: se adaptó el verificador a su nueva ubicación en `src/scripts/ci/`
y se verificó ejecutándolo fuera del repo. Guías y mapa reflejan los scripts,
configuración e imagen frontend reubicados y las excepciones actuales del
selector, sin modificarlo. Pasaron 23 tests del selector, 12 escenarios de
deploy y 16 casos del verificador; 80 documentos sin hallazgos. Estos cambios
de estructura provienen del trabajo adicional presente en el checkout;
#2638 solo ajusta documentación y su verificador.
