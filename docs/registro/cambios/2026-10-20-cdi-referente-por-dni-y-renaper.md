# CDI: referente identificado por DNI y ajustes de RENAPER

Rama `Fix_PedidoEzequiel`. Observaciones de CDI sobre los tickets 2657 y 2658.

## Pedido

1. Al cargar un niño/a en la nómina, cambiar el tipo de documento de un
   responsable (por ejemplo "Ninguna documentación" → "DNI Permanente") dejaba
   cargarlo a mano sin pasar por RENAPER.
2. En el trabajador, el sexo registral no quedaba validado por RENAPER y se
   podía editar.
3. Al cargar como referente a una persona cuyo email ya existía en la base, el
   CDI quedaba con la cuenta de la otra persona. El email suele ser el
   institucional del centro y se repite: hay que cargar a la persona nueva y
   conservar el histórico.

## Causa

1. `cdiRenaperBloques.js` pasaba el bloque a carga manual al elegir un tipo sin
   DNI, pero al volver a un tipo con DNI no lo regresaba al paso de validación.
2. RENAPER informa el sexo como id del catálogo `Sexo`; el alta de trabajador
   lo buscaba como texto ("Femenino"), no lo encontraba y no lo precargaba ni
   lo bloqueaba.
3. `crear_referente_cdi_automaticamente` buscaba un usuario por email y, si
   había uno solo, lo asociaba como responsable sin comparar nombre ni DNI. Al
   cambiar el referente sin cambiar el DNI (o sin DNI en la ficha), se lo
   tomaba como la misma persona y se le cambiaba el email a la cuenta del
   responsable. Caso real: CDI 212, donde quedó como responsable una cuenta de
   otro programa (PWA PNUD) con el email institucional.

## Solución

1. Si el bloque estaba en carga manual por no tener DNI y se elige un tipo con
   DNI, vuelve a pedir el DNI y descarta lo cargado a mano (oculto se enviaría
   igual). La carga manual por "RENAPER no encontró a la persona" no cambia.
   Es solo de pantalla: el servidor sigue aceptando la carga manual.
2. La vista traduce el id de sexo al catálogo, como ya hacía con la
   nacionalidad. Aplica a altas nuevas; los trabajadores existentes no se
   marcan como verificados.
3. El referente se identifica por DNI (el de la ficha o, si falta, el del
   CUIL) y, en fichas o cuentas sin DNI, por nombre y apellido. **Nunca por
   email.**
   - Se reutiliza una cuenta existente solo si es de la misma persona: primero
     entre los usuarios del CDI (recupera un referente histórico) y después,
     por DNI, en toda la base.
   - Si no tiene cuenta, se crea una nueva con sus datos, DNI y CUIL, aunque el
     email ya lo use otra cuenta (el login es por usuario y el blanqueo de
     contraseña por email ya admite varias cuentas).
   - Cambio de persona = otro DNI o, sin DNI, otro nombre. El nuevo queda como
     responsable y el anterior conserva su cuenta, sus datos y su acceso.
   - Si el responsable no es la persona de la ficha, al guardarla se recupera
     o se crea la cuenta del referente. Así se corrigen casos como el del
     CDI 212.
   - El email solo se sincroniza sobre la cuenta del responsable cuando es la
     persona de la ficha.
   - Usuario de los referentes CDI (alta automática y "Generar usuario"): si
     otra cuenta ya usa el email, el usuario es el DNI, como en PNUD; si no,
     se arma desde el email, como hasta ahora. Con un email compartido, el
     usuario salía con el nombre de otra persona (`cpi.centro-2`). Decisión de
     Producto: el DNI solo cuando el email se repite. `generar_usuario_delegado`
     suma la opción `usuario_dni_si_email_en_uso`, apagada por defecto: CDF,
     VAT y trabajadores CDI siguen igual. Una cuenta cuyo usuario es un DNI
     (como las de PNUD) se reconoce como de esa persona.

## Trade-offs

- Si una cuenta sin DNI tiene el nombre distinto al de la ficha (por ejemplo,
  con un segundo nombre), se la toma como otra persona y se crea una cuenta
  nueva. Se prefirió eso a asociar la cuenta de otra persona.
- Cuentas con el mismo DNI en varios usuarios fuera del CDI: no se elige
  ninguna y se crea una nueva.
- Con el DNI solo ante un email repetido, la primera persona que usa un email
  institucional queda con ese email como usuario (`cpi.centro`) aunque después
  deje de ser referente. Cada persona igual tiene su propia cuenta y sus datos.

## Tests

- `test_trabajadores_views.py`: sexo de RENAPER precargado y bloqueado.
- `test_automatic_user_provisioning.py` y `test_gestion_usuarios_cdi.py`: email
  de otra persona → cuenta propia; misma persona por DNI → se reutiliza; nuevo
  referente con el mismo email institucional; responsable ajeno corregido sin
  tocar su cuenta.
