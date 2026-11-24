# Cambio: pantallas React activas por defecto (#2785)

## Qué cambia

- `REACT_VERTICALES_ACTIVAS` sin definir equivale a `todas`: `core.react_activation` expande a todas las claves de
  `REGISTRO`. Antes, vacío = todo en Django.
- Apagado explícito: `REACT_VERTICALES_ACTIVAS=ninguna` (o la variable definida y vacía). Una lista (`pas,cdi`) funciona como antes.
- Sigue exigiendo el build congelado: sin `index.html` en `SISOC_REACT_BUILD_DIR` no se monta nada y no falla.
- Por entorno: QA, HML y producción reciben React al desplegar esta rama si la imagen trae el build
  (`/opt/sisoc-react`) y no definen la variable. Para que un entorno siga en Django: `REACT_VERTICALES_ACTIVAS=ninguna`.
- Docs actualizadas: `docs/operacion/deploy_automatizado.md`, `docs/implementaciones/frontend_v2.md`, `.env.example`.

## Por qué

Subir a QA con React encendido para que lo prueben sin tocar variables.

## Cómo se verificó

- Tests nuevos en `src/backends/kernel/tests/test_react_activation.py`: sin definir = todas, `ninguna`/vacía = ninguna,
  lista explícita, y por defecto con y sin build. Los tests existentes de "sin flag" ya fijaban el flag vacío.
- Los tests de ruteo nativo corren sin build (`SISOC_REACT_BUILD_DIR` vacío), por lo que no montan entradas.

## Limitaciones

- Producción también lo recibe al promover; no hay distinción por entorno en el código.
- Un compose o `env_file` que pase la variable vacía la apaga sin avisar.
- Retorno: `REACT_VERTICALES_ACTIVAS=ninguna` y reiniciar.
