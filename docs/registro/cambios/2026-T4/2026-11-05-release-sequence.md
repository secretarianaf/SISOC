# Promociones adicionales del mismo día

## Motivo y alcance autorizado

El responsable autorizó una segunda promoción hoy preservando el tag original y
todos los gates de SISOC. El PR directo2879 no puede recibir release_baseline:
solo el PR final homologacion→main es elegible. El tag diario existente identifica
el baseline previo a2877, no el main actual. Se incorpora el API selectivo por un
bootstrap acotado a HML junto con esta reparación, nunca todo2878.

## Diseño

Marker opcional release-sequence: ausencia o1 conserva el tag YYYY.MM.DD-stable;
2 selecciona YYYY.MM.DD-2-stable. Un único entero positivo seguro, sin selección
automática ni sobrescritura. El baseline identifica PR/base/head/tag; un cambio
de secuencia no reutiliza un éxito anterior. El tag se congela y se vuelve a
comparar con los datos del PR antes del éxito. Creación, release y reporte usan
la misma identidad. Colisiones, cambios de main/head y secuencia bloquean.

No se cambian YAML, permisos, App, rulesets ni Environment. El workflow existente
carga JS desde HML; sincronizar a development antes del siguiente pre-deploy.
Las plantillas canónicas y sus copias generadas documentan el quinto marker opcional.

## Pruebas y límites

RED observado con los tests nuevos sobre el script anterior: parser ausente,
segunda secuencia usa el primer tag y colisiona, marcadores inválidos elegibles.
GREEN local:30tests de orquestación y sync descendente aprobados, con fixtures
GitHub sin conexión real. Primera secuencia, colisión/idempotencia, secuencia
inválida/duplicada, branch directo y races de main/head/secuencia cubiertos.
Verificación independiente inicial: única carrera nueva durante createRelease reproducida. Corrección acotada: releer main y PR después de publicar el release, antes del baseline exitoso/auto-merge; conservar el tag y release ya publicados si la identidad cambió. Regresión RED observada y GREEN30tests; recheck focalizado independiente aprobado (probe original y regresión), sin baseline exitoso ni auto-merge tras el cambio tardío. CI pendiente. Los ocho tests helper legacy produjeron resultados idénticos sobre baseline y candidato (solo duración normalizada); nueve markers inválidos preservaron hash de estado sin escrituras y los probes de colisión conservaron tags preexistentes. No se ha creado ningún nuevo tag ni
emitido un baseline real. Un test falso registraba args.name sobre la etiqueta de
operación del harness; se corrigió el fixture, no la lógica productiva.

## Rollback

Revertir la unidad de código no borra tags ni datos. Un release adicional ya
emitido exige conservar su nombre exacto e historial. No ejecutar un script viejo
para un PR con secuencia2: podría seleccionar otro tag. La aprobación humana de
production y la verificación de revisión desplegada siguen siendo pasos separados.

Risk: items3,4,5 (marker/tag contract, baseline races, release workflow).
