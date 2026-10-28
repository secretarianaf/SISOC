# HML: permisos persistentes de adjuntos sin root
Objetivo: corregir únicamente HML; producción queda sin cambios. Base desplegada: 2478a213c773b4662cb6119c71c728ba1a629b0b.
Rama: fix/hml-runtime-upload-permissions. Estrategia: single-pr, excepción de tamaño aprobada al autorizar una única PR; previsión inicial 380 líneas propias. Runner: pytest aislado en Linux, sin Django/DB.

## Specs
- S1. Pedido: "parece seguir pasando ese error en otros adjuntos, verifica que no se repita". Comprobar todos los destinos de media, no solamente los dos iniciales.
- S2. Autorización: "autorizo"; alcance confirmado: ampliar permisos de adjuntos en HML y persistir en despliegue sin depender de root, con archivos temporales. Identidad exclusiva de aplicación, recreación de servicios afectados, permisos de media/logs y reversión; conservar propietarios y documentos.
- S3. Confirmación: "confirmo, pero este error se llevara a produccion?". Aislar selección HML; no alterar comportamiento, despliegue ni permisos de producción. No acceder a producción.
- S4. Publicación autorizada el 2026-10-28 mediante "autorizo", en respuesta a una única PR en secretarianaf/SISOC usando la sesión GitHub configurada, sin merge ni deploy a producción. Separar tests aislados, CI, verificación HML y aceptación HTTP/humana.

- S5. Usuario: "1, pero ademas has un plan para que esto no vuelva a pasar y no pase en produccion, quizas haciendo lo de los permisos en cada deploy". Preparar un plan de prevención por deploy para ambos entornos; producción continúa sin acceso ni cambios autorizados.

## Tasks
- T1 | S1-S3 | inline, lectura preparatoria comprimida por verificador de riesgo | implementación y checks locales completos; commit pendiente | pruebas RED de ACL/herencia y selección HML; permisos y configuración con conservación de acceso existente.
- T2 | S1-S4 | inline, despliegue HML autorizado | pendiente | backup previo, aprovisionar permisos y recrear servicios sin migraciones; validar sin root y preservar datos.
- T3 | S1-S4 | verificación independiente (riesgo 2 y 5) | verificación local/nativa completa; HML pendiente | 29 tests y revisión cerrada, aceptación de runtime pendiente.

- T4 | S5 | inline, documento de planificación | preparado | plan con fases, gates, aceptación, límites y autorización separada de producción.

## Log
- L1. Usuario: "me reportan que en hml no se estan pudiendo subir archivos"; "error 400 y \"no se pudo guardar el archivo\"".
- L2. Corrección inicial: ACL UID1004 en dos directorios; pruebas temporales satisfactorias. Usuario luego informa S1.
- L3. Verificación posterior: 96 directorios; UID1004 puede escribir en 4, no en 92. Contenedores recreados a las 12:25:56 ejecutan root; no se atribuye ese cambio a este trabajo. Las ACL iniciales siguen presentes.
- L4. Autorizaciones S2/S3 recibidas. Git local original está detached en 7ef5b32ff, con cambios ajenos, y no contiene el monorepo desplegado. Se preserva intacto; revisión HML obtenida por SSH autorizado y worktree aislado desde su SHA exacto, sin publicación. Excepción al inicio desde development: reparación operativa contra la revisión efectivamente desplegada.
- L5. Ruta: C:/Users/Juanito/Desktop/Repositorios/NACION/SISOC-worktrees/hml-runtime-upload-permissions. Lectura remota identificó 17 escritores de media más procesos de logs/scheduler. Dockerfile/Compose no fijan identidad no-root común; un cambio solo en entrypoint no cubre Gunicorn directo.
- L6. Diseño confirmado: identidad de aplicación exclusiva en HML, conservando propietarios mediante ACL de acceso/herencia. UID10001 disponible en host; GID1016 corresponde al grupo existente de despliegue. Migrador y producción no cambian. Previsión: el alta de la corrección en futuras revisiones upstream necesita publicación explícita; no afirmar persistencia upstream con un parche remoto suelto.

- L7. ACL/helper y selector HML implementados con RED/GREEN. Suite aislada Linux: 27 tests verdes; Bash syntax y Black check correctos, lint E/F sin errores. Ningún cambio adicional en servidor o producción. La suite detectó un fixture modificado por reemplazo amplio; se corrigió y la suite completa quedó verde. Backup privado, herencia, conservación de permisos efectivos y datos cubiertos.

- L8. Verificador independiente: 27 tests, probes adicionales, diferencial QA/PRD (stdout/stderr/exit) y mapa de 18 servicios correctos. Parent spot check: Compose real --profile '*' con .env sintético confirma 18 identidades10001:1016, migrador sin cambios y overlay ausente de producción. Ninguna carga ni cambio de configuración real todavía.
- L9. El helper, tests y overlay son una sola unidad de riesgo inseparable: no iniciar procesos no-root sin permisos ni desplegar permisos sin verificación de usuario. El tamaño final supera la previsión inicial (formato Black y tests incluidos); no dividir artificialmente ni publicar sin estrategia de entrega acordada.

- L10. Usuario: "1, pero ademas has un plan para que esto no vuelva a pasar y no pase en produccion, quizas haciendo lo de los permisos en cada deploy". Consentimiento granted para el candidato; planificación preventiva de producción, no autorización de cambios allí.
- L11. Revisión nativa de cuatro lentes encontró R1-001 (ACL default podía ampliar lectura futura ignorando umask) y R3-001 (entrada nominada no habilita al mismo UID dueño restrictivo). Ambos reproducidos RED; corrección limitada a helper/tests: default nueva sin grants de grupo/otros y ampliación del owner solo si es UID objetivo. 29 tests GREEN, Black check y Pylint E/F sin errores. Validación dirigida aprobada; acknowledge exacto con schema gentle-ai.review-acknowledged/v1 y authority=burned, linaje review-00fa887f10c13dfe, target65946b58dde9e61cb8032e472be6c2fab357c7c2f3243d947fb7af4bbb6ffc40. No reiniciar esa revisión ni reutilizar su autoridad.
- L12. Plan preventivo guardado en docs/plans/2026-T4/2026-10-28-prevencion-permisos-adjuntos-hml-produccion.md: controles por deploy y producción propuestos, no implementados. Antes del corte, escritura efectiva como UID de app; después del arranque, health + permisos + prueba sintética; CI, alertas, reversión probada y promoción separada. Ampliación completa pendiente: el candidato actual aplica ACL después de down en el flujo completo y no tiene rollback automático.
- L13. No hay nuevo despliegue HML, cambios de ACL reales ampliados, acceso a producción, commit ni publicación. Para persistencia upstream falta autorización de publicación y estrategia de entrega para la unidad coherente de más de 400 líneas. Los documentos posteriores al cierre son registro/plan, sin nuevas modificaciones funcionales.

- L14. Usuario: "autorizo" (publicar una única PR). Identidad GitHub verificada: juanikitro. Base origin/development actual59a8f797 incluye health_urls_worker y front_inet; se trasladará exclusivamente nuestro cambio a una rama nueva desde esa base, preservando ambos aportes. Se acepta la unidad coherente sobre400líneas, sin eliminar tests/docs ni usar excepcion-calidad. Merge y producción excluidos.
