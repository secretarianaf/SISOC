# Seguimiento SIPH: PDF sin los comentarios del área, el mismo en SISOC y Gestionar (#2651)

## Feedback de QA (jcamiloparra, 14/10)

1. La descarga de SISOC era un docx y conservaba los comentarios que el área
   dejó para el desarrollo (globos "Gescom: …"). Tiene que ser PDF y sin
   comentarios.
2. Gestionar mostraba su PDF genérico de formulario. Tiene que mostrar la
   misma versión que SISOC.

## Causa

La plantilla se derivó del docx "con comentarios GESCOM" del issue y se
conservaron sus 18 comentarios. Eran indicaciones para el desarrollo, no
texto del formulario. QA adjuntó el mismo formulario sin esos comentarios.

## Cambio

- `relevamientos/scripts/armar_plantilla_siph.py` quita las marcas de
  comentario y la relación con `comments.xml`. Además falla si la plantilla
  conserva comentarios o textos de trabajo ("Gescom", "precargado en la app",
  "Comentario"). La plantilla se regeneró desde el docx limpio de QA.
- La descarga es PDF: la plantilla completada se convierte con LibreOffice,
  igual que la certificación de prestaciones y los informes de admisiones.
  `seguimiento_pnud_docx` pasa a `seguimiento_pnud_pdf` y el botón dice
  "Descargar PDF".
- `GET /api/territorial/comedores/{id}/seguimientos-pnud/{pnud_id}/pdf/`:
  Gestionar descarga ese mismo archivo, sin armar uno propio. Solo para el
  SIPH (404 en los demás). Mismo alcance de zona que el resto de la API PNUD.
- La firma del entrevistado va como imagen, leída del storage dentro de
  `firmas/<comedor>/`. Antes salía el texto "(firma registrada)", que no es
  del formulario.
- La casilla vacía pasa de "☐" a "□": "☐" no está en las fuentes del
  servidor y LibreOffice la dibujaba rota. "□" y "☒" salen de la misma fuente.

## Verificación

`tests/test_seguimiento_siph_2651.py`: la plantilla no tiene comentarios ni
textos de trabajo; el PDF trae las respuestas y ninguno de esos textos; la API
de la app devuelve el mismo PDF y 404 fuera del SIPH o de la zona; la firma
entra como imagen y una URL ajena no.
