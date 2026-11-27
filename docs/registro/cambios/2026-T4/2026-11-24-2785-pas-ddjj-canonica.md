# DDJJ pública de PAS en la URL canónica

La imagen de `backend_pas` incluye el build de `apps/pas` en
`/opt/sisoc-pas-react`. El Compose estándar indica ese directorio al runtime.
No se agrega un contenedor de frontend ni se publica `/v2/pas/`.

## Comportamiento

- Una invitación disponible y su página de confirmación mantienen las URLs
  canónicas y sirven React sin exigir login. Django conserva el control de
  disponibilidad, la política de sesión P1 y el envío con CSRF.
- Las invitaciones inexistentes, vencidas o usadas conservan la respuesta nativa.
  El archivo PDF sigue privado y no se modifica su descarga.
- Los assets versionados se sirven bajo `/pas/ddjj/react/assets/`, en el mismo
  backend. El CSS compartido de PAS permanece bajo `/static/`.
- Un cambio limitado a `apps/pas` recrea solo `backend_pas`, sin migraciones.
  Los otros backends no compilan ni incluyen los assets de PAS.

## Verificación y reversión

- Las pruebas HTTP usan el URLconf del runtime con datos sintéticos. Cubren
  invitación, confirmación, assets, restricciones de sesión, envío y retorno a
  Django con activación apagada o sin el build. SQLite no reemplaza la
  validación contra MySQL.
- Se ejecutaron las pruebas de selección de deploy, el build y las pruebas de
  la app PAS. Se verificó que los archivos JS y CSS del índice existan en el
  stage Docker para PAS y que ese stage no genere el índice para VPSL.
- En la imagen final de PAS, con el cliente de Django y sin red, la
  confirmación anónima y los assets del build respondieron 200. El acceso directo
  a media privada respondió 404.
- Para volver a la UI Django, quitar `pas` de la lista de
  `REACT_VERTICALES_ACTIVAS` y reiniciar el runtime. Eso también desactiva las
  pantallas React del backoffice PAS, sin cambiar sus URLs.
- Sigue pendiente la comprobación en navegador del flujo real por el proxy del
  entorno y su aceptación. No se desplegó a ningún entorno compartido.
