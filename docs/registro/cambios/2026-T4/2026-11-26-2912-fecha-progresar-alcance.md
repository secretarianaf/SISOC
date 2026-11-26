# Cambio: fecha de carga dentro del alcance de Progresar (#2912)

## Alcance

El tablero Progresar Curso recortaba sus filas por provincia pero calculaba la fecha de carga sobre todas las provincias. La fecha puede revelar actividad fuera del alcance de la persona.

## Comportamiento

La fecha máxima se calcula sobre el mismo conjunto autorizado que los datos de resumen. Una persona con acceso nacional conserva la fecha máxima nacional; sin filas autorizadas, la fecha queda vacía. No se cambia quién puede abrir el tablero ni se activa aún la nueva política de audiencias.

## Verificación

Una prueba con fechas distintas entre provincias reprodujo la discrepancia y verifica la respuesta de la vista y el resultado nacional. La suite local del tablero pasó con tablas BI sintéticas en Docker. La revisión independiente comprobó alcance de varias provincias, nacional y provincia sin filas; sus pruebas se incorporaron. Pylint aprobó el archivo. El usuario confirmó la aceptación visual con la demo sintética.

## Limitaciones

No se accedió a tablas reales ni se verificaron datos de producción. Falta integrar el nuevo contrato de audiencias, rutas y datos, además de acordar su activación con Datos. No hubo publicación ni despliegue.
