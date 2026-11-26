# Cambio: assets React bajo prefijos que llegan al backend que monta la entrada (#2785)

## Qué cambia

Hotfix sobre QA con React activo por defecto. Solo cambian las URLs de los assets; el HTML y el aspecto son los mismos.

| Entrada | Antes | Ahora | Causa |
| --- | --- | --- | --- |
| Login e identidad (`sisoc_core/usuarios/identity_preview.py`) | `/static/sisoc-identity/assets/` | `/sisoc-identity/react/assets/` | Nginx sirve `/static/` de disco: 404 y login en blanco. |
| Relevamientos (`comedores/relevamientos/web_preview.py`) | `/comedores/react/relevamientos/assets/` | `/comedores/react/assets/` | La ruta `comedores/react/<path:...>` de otra entrada, montada antes, la tapaba y buscaba `relevamientos/assets/...`. |
| Convenio tarjeta, intervenciones, observaciones (comedores) | `/convenio-tarjeta/`, `/intervenciones/`, `/observaciones/` + `react/assets/` | `/comedores/react/assets/` | Ninguno está en `url_prefixes` de comedores: el core no los reenvía y responde 404. |

Las entradas comparten el build `sisoc`, así que `/comedores/react/assets/` sirve los mismos archivos; `react_preview_patterns`
monta una sola vez la ruta repetida. `/pas/ddjj/react/` sigue sin montarse sin `SISOC_REACT_PAS_BUILD_DIR`, igual que su HTML.

## Por qué

Una pantalla React cuyo JS da 404 queda en blanco.

## Cómo se verificó

- Guarda nueva `test_assets_de_cada_entrada_llegan_al_backend_que_la_sirve` (`src/backends/kernel/tests/test_react_activation.py`):
  para cada clave de `REGISTRO` con build, cada asset reescrito en el `index.html` no empieza con `/static/` ni `/media/`, se
  enruta por `url_prefixes` al mismo backend que la entrada y su vista responde 200. Falló sobre `origin/development` con
  exactamente los cinco casos de arriba y pasa con el cambio.
- Tests de las entradas tocadas actualizados al prefijo nuevo.

## Limitaciones

- La guarda usa un build sintético; no valida un build real ni la configuración de Nginx desplegada.
- No toca `url_registry.json`: las entradas React no figuran ahí.
