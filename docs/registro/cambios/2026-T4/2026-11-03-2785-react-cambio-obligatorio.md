# Cambio: transporte backend de contraseña obligatoria (#2785, ID-C)

## Corte backend actual

Esta unidad incorpora únicamente el API de cambio obligatorio, sus pruebas y la
extracción del procedimiento existente para compartirlo con la vista HTML nativa.
No incluye React, otra entrada HTML, activación global ni cambios de política.
La verificación aislada pasa con 119 pruebas de cambio obligatorio, login, sesión
y requisitos; Black en seis Python, Pylint y referencias documentales. Persisten
siete avisos previos. Se usó la imagen local fijada sin red, código de solo
lectura y datos SQLite sintéticos; sin navegador, TCP ni recuperación visual.

Ocho regresiones de HEAD observaron cuatro fallos internos y cuatro casos
externos correctos. Se añadió únicamente `/api/web/password/first-change/` a
la excepción del adaptador admindocs propio, conservando login y categorías.
El test diagnóstico histórico se sustituyó por el contrato privado de la API;
no cambia admindocs fuera de esa ruta ni incorpora el cambio voluntario pendiente.

La comprobación independiente pasa 16 GET/HEAD internos/externos con acceso,
privacidad y datos conservados, 104 comparaciones directas del middleware y
cuatro POST nativos aislados contra el baseline. La extracción conserva errores,
redirects, mensaje, contraseña, flags, temporales, sesión y tokens. La presentación
legacy no habilita capacidades ni `navigation` de sesión pendiente. Las
comparaciones de middleware no constituyen una suite HTTP adicional.

Los dos blobs corregidos coinciden con GREEN. El archivo Git conserva su formato
de checkout; no se confunden bytes CRLF con los blobs LF. Requiere revisión
técnica por afectar sesión, procedimiento compartido y configuración. Estas
pruebas no acreditan paridad visual, aceptación humana, CI ni despliegue.

Las secciones siguientes preservan el registro histórico del circuito completo.
Sus pruebas de UI, capturas y resultados no son evidencia nueva ni aceptación del
corte backend actual.

## Registro histórico del circuito completo

## Alcance

Se incorpora la UI específica y el API web por sesión para el cambio obligatorio
de contraseña. El contrato y sus límites se siguen en
`odd/tasks/react-global-2785.md`, S5/T9/T11, y en
el contrato histórico de remediaciones de identidad (no incluido en este corte).

La integración de la ruta HTML y del marco compartido pertenece al coordinador.
Este cambio no activa React en rutas públicas desplegadas, no modifica el login
PWA/token ni altera permisos, validadores, dependencias o configuración global.

## Comportamiento

`src/backends/sisoc_core/usuarios/required_password_change.py` conserva la
secuencia de la vista anterior: guardar mediante `SetPasswordForm`, limpiar el
requisito y sus campos temporales, actualizar el hash de la sesión y emitir el
mismo aviso. No se agregan revocación de tokens, locks, limpieza adicional ni
una transacción que cambie el comportamiento existente ante fallos parciales.

`src/backends/sisoc_core/usuarios/web_required_password.py` expone el recurso
`/api/web/password/first-change/`:

- GET/HEAD entrega únicamente los dos descriptores del Form, el requisito y el
  DTO de presentación autorizado. El menú representa el HTML heredado; no
  concede acceso a datos ni operaciones.
- POST recibe `application/x-www-form-urlencoded` y conserva los errores del
  Form. El usuario se obtiene de la sesión, nunca de un ID del payload.
- Sesión ausente: 401. Acceso web deshabilitado o CSRF inválido: 403. JSON no es
  transporte de mutación: 415. Los métodos no soportados devuelven 405.
- Si el requisito ya fue resuelto, devuelve el destino fijo generado con
  `reverse("inicio")`, sin volver a guardar la contraseña.
- Todas las respuestas del recurso son privadas, no-store y varían por Cookie.
  No se amplían excepciones de middleware ni se cambia el diagnóstico XView
  interno/staff. El HEAD público se verifica con origen externo sintético.

El API reevalúa sesión/acceso porque `/api/` ya estaba excluido de los redirects
de prerrequisitos. No exige `ready` para resolver el requisito de contraseña,
pero conserva la denegación superior y la posterior confirmación/encuesta.
`/api/web/session/` sigue devolviendo `navigation: []` mientras hay requisitos.

`RequiredPasswordChange.tsx` (componente histórico no incluido) conserva los campos,
ayudas y errores de la pantalla anterior. Usa el cliente de sesión/CSRF existente
y entrega el contenido al marco mediante `renderFrame`, sin simular un contexto
ready. Las contraseñas sólo viven en el formulario local y se limpian después de
cada respuesta/rechazo; no se registran ni persisten. Las respuestas tardías de
una pantalla desmontada se ignoran. Un resultado incierto deshabilita otro POST
hasta que la persona revise el estado; no se reintenta automáticamente.

## Verificación

Los tests están en
`src/backends/sisoc_core/tests/test_web_required_password.py` y
`RequiredPasswordChange.test.tsx` (prueba histórica no incluida).

Se observó RED de requests públicos por ruta ausente antes de la implementación.
Las comprobaciones se ejecutan en una copia aislada, con imagen Python existente
fijada, fuente readonly, SQLite sintética y sin red saliente. El frontend utiliza
Node y dependencias existentes, sin instalación en el repositorio.

Se verificaron los 18 casos del API por la ruta pública registrada, los 10 tests
del componente, TypeScript y ESLint de la superficie propia, Black y Pylint de
los tres archivos Python propios. La integración de identidad y los flujos
previos de sesión, prerrequisitos, cuenta y autenticación pasaron en una única
selección de ocho módulos (190 tests). La corrección acotada de lint compartido
se volvió a verificar con Black/Pylint y los cuatro tests del preview, sin
repetir la selección completa. Persisten avisos heredados de Django/WeasyPrint.

La matriz canónica ID-C se ejerció mediante requests y navegador real en cuatro
situaciones, desktop 1440×900 y mobile 390×844, con 16 estados aislados de fuente
y candidato. Las ocho comparaciones de página completa resultaron idénticas en
píxeles, con delta geométrico máximo de 0 CSS px, sin máscaras ni dispensas
nuevas. Se verificó Tab entre los dos campos, la limpieza de valores rechazados,
los hashes sin cambios tras rechazo/retorno temprano y los efectos del guardado
con sesión conservada y posterior confirmación de perfil. Cada POST previsto
se ejecutó una vez por estado, sin repetir una mutación incierta.

El registro de URLs conserva todas las entradas previas y coincide exactamente
en las dos entradas nuevas de identidad. La comparación integral en modo dev
mantiene la diferencia heredada de diez rutas de preview locales, reproducida
en la copia inmutable previa de INS-B; no se incorporaron esas rutas al registro
productivo para ocultar la diferencia.

La comparación utiliza solamente recursos existentes de caché verificados por
hash, fuente readonly y estado sintético. La composición WSGI temporal deriva
únicamente el prefijo estático exacto del preview a su URLconf real, evitando que
el servidor de archivos de desarrollo lo intercepte; no modifica middleware,
guards ni rutas públicas desplegadas. La revisión independiente, aceptación
humana, revisión nativa, CI y despliegue son estados separados y no se deducen
de estos resultados. No se hizo commit ni publicación.

Riesgo técnico: autenticación/prerrequisitos, contrato de sesión, respuestas
asíncronas e integración de rutas. Los cambios compartidos y la activación siguen
fuera de la superficie del escritor de este circuito.
