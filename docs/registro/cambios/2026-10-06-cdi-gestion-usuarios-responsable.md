# CDI: responsable del centro y botonera de usuarios

Rama `Renaper_CDI`. Sin ticket al momento de implementar.

## Pedido

- Cuando en la ficha del CDI se cambia el referente, el anterior **no** se da de
  baja automáticamente: puede seguir ejerciendo tareas.
- El único que puede inhabilitarlo o darlo de baja es el **nuevo responsable**
  del centro.
- En "Usuarios del centro", el responsable ve una **botonera** para manejar el
  alta, la suspensión y la baja de los usuarios.

## Estado previo

- El panel "Usuarios del centro" solo listaba usuarios (Activo/Baja), sin
  acciones. Nada en el código daba de baja un `AccesoCDI`.
- El referente veía solo su propia fila; generar usuarios era exclusivo de EGP y
  usuarios territoriales con delegación del grupo "CDI - Referente centro".
- Al cambiar el referente en la ficha: no se creaba usuario para el nuevo (el
  alta automática solo ocurría si el CDI no tenía usuarios) y, si el email
  cambiaba, `sincronizar_email_referente_cdi` **pisaba el email de la cuenta del
  referente anterior** cuando todavía tenía la contraseña temporal. Si la
  persona era otra, la cuenta del anterior pasaba al nuevo.

## Solución

**Modelo `AccesoCDI`** (migración 0051):

- `estado`: activo / suspendido / baja. Es la fuente de verdad; `activo` se
  sincroniza al guardar, así las consultas existentes (alcance, permisos,
  reportes) siguen usando `activo=True` sin cambios.
- `es_responsable`: el referente vigente de la ficha, uno por CDI.
- `motivo_estado`: motivo de la última suspensión o baja.
- La migración completa el estado desde `activo` y marca como responsable al
  acceso activo cuyo email coincide con el del referente de la ficha; si
  ninguno coincide, al acceso activo más antiguo.

**Permisos** (`access.py`):

- `puede_administrar_usuarios_cdi`: quien gestiona referentes en el territorio
  (EGP, superusuario) o el **responsable** del propio CDI. Los demás referentes
  ven solo su fila, como antes.
- Generar usuario queda habilitado para quien administra y hay cupo.
- El cupo lo ocupan activos y suspendidos; la baja lo libera.

**Generación por el responsable**: `generar_usuario_delegado` (kernel) acepta
`delegacion_autorizada`, que el dominio usa después de validar su propia regla
acotada. Así el responsable genera referentes solo para su CDI sin darle al
grupo "CDI - Referente centro" la delegación de sí mismo en general (que le
permitiría asignarlo en otros flujos).

**Botonera** (`services_accesos_cdi.cambiar_estado_acceso` + endpoint
`centrodeinfancia/<pk>/usuarios/<acceso_id>/estado/`):

| Acción | Desde | Hacia | Motivo |
|---|---|---|---|
| Suspender | Activo | Suspendido | Obligatorio |
| Reactivar | Suspendido | Activo | — |
| Dar de baja | Activo o suspendido | Baja (definitiva para el CDI) | Obligatorio |

Resguardos: nadie cambia su propio acceso; **el responsable no se puede
suspender ni dar de baja** (se reemplaza cambiando el referente en la ficha),
así el CDI nunca queda sin responsable; la baja corta el acceso a ese CDI, no la
cuenta de la persona. Cada cambio queda en la auditoría ("Acceso CDI").

**Cambio de referente en la ficha** (`actualizar_referente_cdi`):

- CDI sin usuarios: se crea el referente inicial como responsable (como antes).
- **Cambió el DNI** del referente: es otra persona. Se crea o vincula su
  usuario como nuevo responsable; el anterior conserva su acceso como
  referente común. No se toca el email de la cuenta anterior.
- Mismo DNI con otro email: se sincroniza el email de la cuenta del
  responsable (comportamiento previo).
- Sin DNI anterior (fichas viejas) no se puede saber si cambió la persona: se
  trata como la misma.

## Definiciones de producto

Confirmadas por producto:

1. Suspendido = temporal y ocupa cupo; baja = definitiva y libera cupo.
2. El EGP también tiene la botonera.
3. Solo el responsable y el EGP generan usuarios; los demás referentes no.

## Antes de desplegar: revisar producción

La migración elige un responsable por CDI. Conviene ver de antemano los casos
ambiguos:

```sql
-- CDI con más de un acceso activo (el responsable sale del email de la ficha
-- o, si no coincide ninguno, del acceso más antiguo)
SELECT a.centro_id, c.nombre, c.email_referente, COUNT(*) AS activos,
       SUM(LOWER(u.email) = LOWER(c.email_referente)) AS coinciden_email
FROM centrodeinfancia_accesocdi a
JOIN centrodeinfancia_centrodeinfancia c ON c.id = a.centro_id
JOIN auth_user u ON u.id = a.user_id
WHERE a.activo = 1
GROUP BY a.centro_id, c.nombre, c.email_referente
HAVING COUNT(*) > 1;
```

Si `coinciden_email` es 0 o mayor a 1, el responsable elegido es el más
antiguo: revisar esos CDI con el equipo funcional.

## Validación

`src/backends/cdi/centrodeinfancia/tests/test_gestion_usuarios_cdi.py`: estado y
cupo, permisos del responsable (incluido otro CDI y responsable suspendido),
botonera y transiciones inválidas, protección del responsable y del propio
usuario, generación por el responsable, cambio de persona en la ficha, cambio
de email de la misma persona y reactivación de un referente existente.
