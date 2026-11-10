# Contratos fuente y cobertura por ruta: alcance de la profundización

Estado: **E2, planificación**. I1 ya está elegida: Django es la referencia
visual INET; backend integrado se reutiliza. Los registros siguientes avanzan
los puntos 1–4 y sirven para refinar tareas del punto 5. No son contratos API
operativos ni evidencia de pantallas ejecutadas.

## Registros que se pueden consultar

| Registro | Qué contiene | Qué no demuestra |
|---|---|---|
| [Contratos fuente](2026-10-27-2786-contratos-fuente.json) | 614 declaraciones de las 95 familias; definición por símbolo, attrs/form/bases, handlers explícitos, callbacks, respuestas y evidencias de acceso/scope | Métodos efectivos heredados, exposición runtime, equivalencia de scope o nuevo schema completo |
| [Impacto visual fuente](2026-10-27-2786-impacto-visual-fuente.json) | Grafo conservador de 509 templates HTML y 4 templates de texto backend, dependencias literales/dinámicas, assets, nombres de URL y paquetes frontend | Que todas las ramas/loader/imports se hayan ejecutado o que un recurso sea pantalla independiente |
| [Cobertura visual integral](2026-10-27-2785-cobertura-visual-integral.json) | Una obligación explícita por cada declaración y por cada familia; cadenas de templates, respuesta, fixture pendiente y evidencia requerida | Capturas, fixtures creadas, roles concretados, baseline aceptado o una comparación ya aprobada |

La fuente de rutas sigue en `ae0b0da01c546d801f18237c3c6dab29a5496790`, junto
con el delta conocido. Las definiciones y dependencias de esta continuación se
leyeron en `59a8f797688c9e762d5a4e9eaa187698ffade8aa`: 196 archivos Python
necesarios, sin importar el proyecto, con 632 símbolos/bases distintos y 85 forms
localizados. Las evidencias de permiso antiguas conservan su origen explícito;
si cambió el caller/helper, se cotejan con esa nueva fuente antes del contrato.

## Precisión del contrato y métodos

Los handlers GET/POST/etc se separaron de hooks como `get_queryset`, que no son
métodos HTTP. Las bases y decoradores siguen presentes para revisar dispatch
efectivo; no se publica una allowlist deducida del nombre ListView o de un hook.

Los forms resueltos conservan Meta.fields/model/labels/widgets y campos
declarados, más puntos de validación/init/save. Campos heredados o querysets
dependientes del usuario/instancia no se inventan. El contrato futuro reutiliza
esas reglas, define su proyección/errores explícitamente y verifica los negativos
antes de generar tipos. No se serializa un ModelForm/ORM completo por automatismo.

Las 111 clasificaciones genéricas iniciales se precisaron siguiendo retornos,
helpers y bases del proyecto: no queda una declaración sin tipo de respuesta
fuente. Esto no prueba dispatch efectivo, serializers completos ni scope en
ejecución. El registro mantiene `API_contract_accepted=false` y validación runtime
pendiente, en lugar de declarar 614 contratos operativos cerrados.

El formato de evidencia v2 indexa cada símbolo una vez: `definition_refs` y
`project_base_refs` apuntan a `view_definitions` del mismo archivo; `form_ref`
apunta a `forms`. Los `historical_*_evidence_refs` siguen apuntando al índice
original. No confundir IDs locales de ambos archivos ni repetir bases completas
para aparentar más evidencia.

## Hallazgos que evitan pantallas inventadas

- `ImportDatosView` y `BorrarDatosImportadosView` nombran templates ausentes,
  pero sus métodos GET devuelven 405 (solo POST) y sus POST redirigen. No crear
  dos pantallas nuevas a partir de esos atributos; comprobar operación, mensajes,
  status y pantalla de destino. Se conservaron referencias históricas y se
  corrigió la interpretación visual del registro, sin tocar aplicación.
- `OCRDocumentDownloadView` devuelve texto adjunto y controla dueño del job.
  `.txt` es sufijo del archivo, no un template. Mantener descarga/404 y UI padre.
- Los textos de email/reset son recursos backend reales, no pantallas React.
  Se incluyen en el grafo para no borrarlos al retirar presentación compartida.
- El template de acompañamiento con `ñ` sí existe. La lectura del índice usa
  paths Git delimitados por NUL para no confundir quoting de nombres Unicode
  con un archivo faltante. No se renombra ni corrige un template válido.
- Queda una referencia HTML sin archivo localizado: la lista de espera CDF
  independiente. El responsable eligió [W1](2026-10-27-cdf-lista-espera-decision.md):
  usar sección existente y compatibilidad de URL. No se inventa una pantalla
  ni se afirma un fallo de producción; tarea futura [#2811](https://github.com/secretarianaf/SISOC/issues/2811).

## Consumidores indirectos: cómo usar el registro

El grafo localiza 371 declaraciones candidatas consumidoras de `includes/main.html`
y 380 de `includes/base.html`. Son declaraciones del snapshot, con aliases y
ramas posibles, no 371/380 pantallas activas ni una cifra de capturas ejecutadas.
También relaciona 149 entradas de assets con sus rutas candidatas.

Antes de cambiar un recurso compartido, obtener su cierre inverso en ese grafo,
reconciliar aliases/actividad por runtime y completar las partes dinámicas. No
limitar el diff al módulo del PR. El grafo de cinco paquetes muestra que
Celiaquía, VPSL e INET declaran dependencias de `@sisoc/api` y `@sisoc/ui`:
los excluidos de migración siguen necesitando regresión si se toca lo compartido.

Cinco declaraciones atraviesan dependencias dinámicas en tres templates. Se
enumeraron sus ramas fuente: ayuda escuelas/asignaciones y curso VAT con
`modal=1` embebido o shell normal. También se materializaron las diez URLs de
importación y nueve paths React INET; no se dejan solo como prefijos abstractos.
Los renderers Python y estados contextuales siguen referenciados en el registro;
si la fuente no permite probar
la rama, en fase autorizada usar trazas de templates de tests Django y navegación
Playwright con fixtures. No instalar observabilidad de producción para este fin.

El registro conservador no reemplaza investigar JS/network ni rutas React
dinámicas. El manifiesto exige relacionarlas con cada UI, incluyendo las rutas
INET bajo I1 y las diez rutas materializadas de importación ya identificadas.

## Cómo pasa una fila a tarea implementable

1. Seleccionar slice y rutas exactas; confirmar método/retorno y caller real.
2. Completar campos/estados/errores con el form/service referenciado y el perfil
   de acceso; resolver el scope que la fuente deja ambiguo sin inventarlo.
3. Reutilizar API existente solo después del contraste por acción/campo/rol.
   Localizar el remanente y sus dependencias en el catálogo.
4. Instanciar paths/roles/estados sintéticos y vincular UI consumidora; llenar
   baseline/candidato/viewport cuando haya ejecución autorizada, nunca ahora.
5. Añadir validación negativa, compatibilidad y retorno, más revisión técnica
   si toca identidad/config/paquetes. Refinar el issue existente o derivar uno
   acotado; no crear 214 tickets automáticamente.

W1 afecta solo la lista de espera independiente CDF; no revoca I1. La
[ficha acotada](2026-10-27-2785-fichas-prioritarias.md) se derivó a #2811 sin
autorizar su ejecución. La siguiente definición material está en
[avisos y unidad de activación](2026-10-27-2788-avisos-y-unidad-activacion.md):
preservar feedback al volver de una operación legacy a una página React.

Validación: integridad JSON, cobertura exacta de familias/IDs, símbolos fuente,
grafos/referencias y correcciones verificadas en métodos/archivos. Sin HTTP, DB,
servidores, browser, capturas, tests de aplicación, CI, commits ni despliegue.
