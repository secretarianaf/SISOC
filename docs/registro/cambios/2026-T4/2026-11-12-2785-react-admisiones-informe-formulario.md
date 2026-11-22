# Cambio: esquema efectivo del formulario del informe técnico sobre G1 v1 (#2785, AD02.01, segunda entrega)

## Alcance

Primera parte del editor del informe técnico
(`comedores/admision/informe_tecnico/<tipo>/<admision_id>/crear/` y `.../<pk>/editar/`), según los
gates 1 y 2 del [contrato AD02](../../../plans/2026-T4/2026-10-28-2785-admisiones-informes-documentos-m2.md):
snapshots nativos por tipo y condición, y una API de solo lectura que proyecta el formulario
efectivo. No incluye todavía la pantalla React del editor ni el guardado por API: guardar
borrador, finalizar, generar el DOCX y los errores siguen en el POST nativo. Las brechas de
acceso se conservan según la [decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos: `src/backends/comedores/admisiones/web_api_informe_formulario.py`,
`web_api_informes_urls.py` (rutas nuevas), `config/url_registry.json` (regenerado),
`config/middlewares/admindocs.py` y la prueba `test_web_api_informe_formulario_ad02.py`.

## Comportamiento

- `GET /api/web/comedores/admisiones/informes/<tipo>/admision/<admision_id>/formulario/` (alta) y
  `.../<tipo>/<pk>/formulario/` (edición) ejecutan `InformeTecnicosCreateView` e
  `InformeTecnicosUpdateView` (`get_form_class`, `get_form_kwargs`, `get_context_data`) y devuelven
  solo los campos que sobreviven a la configuración del `Form` nativo: presencia, obligatoriedad,
  valor inicial, opciones, ayuda, antecedentes de renovaciones, publicación de plantilla (o su
  error y el detalle copiable), observaciones y campos a subsanar. No se serializa el modelo ni se
  aceptan campos del cliente; leer un campo no concede escritura.
- Acceso igual al nativo (alguno de `comedores.view_comedor`, `admisiones.view_admision` o
  `acompanamientos.view_informacionrelevante`, superusuario incluido). Admisión o informe
  inexistente: 404. Tipo distinto de `base`/`juridico`: 400 con el mensaje nativo «El tipo de
  informe seleccionado no está disponible para carga online.».
- El GET es siempre de borrador (`require_full=False`); la obligatoriedad de «Finalizar» se
  verifica contra el formulario nativo en las pruebas.

## Snapshots nativos (gates 1 y 2)

Por `base` y `juridico` × incorporación, incorporación Ex PNUD vigente, renovación primera,
renovación con informe complementario y segunda renovación, en borrador y finalizar
(cantidad de campos / obligatorios al finalizar): base 100/98, 101/99, 131/129, 133/131, 135/132;
jurídico 97/94, 98/95, 127/124, 129/126, 143/136; en borrador ningún campo es obligatorio. La
prueba fija las reglas: sin `resolucion_de_pago_*`/`monto_*`, ni `conclusiones` ni
`antecedentes_renovaciones`; `expediente_incorporacion`/`convenio_incorporacion` y
`aprobadas_ultimo_convenio_*` solo en renovación; `finalizacion_convenio_pnud_vigente` solo en
incorporación Ex PNUD vigente; `presentacion_avales` solo en renovación base; `if_it_complementario`
solo con informe complementario; base sin `validacion_registro_nacional` e
`IF_relevamiento_territorial`; jurídico sin avales y declaraciones.

## Verificación

Entorno sintético, sin red. Pruebas de `admisiones`, `web_gate`, `backend_proxy` y
`servicios_backends`, `black`, `pylint` y `makemigrations --check`.

## Limitaciones

- Falta la pantalla React del editor (secciones colapsables, selectores geográficos, aviso de
  cambios sin guardar), el guardado por API y la verificación visual y G1 de esta parte. El
  efecto de guardar tras error de publicación, el rollback de generación y la subsanación
  (gate 2, efectos) quedan para esa entrega.
