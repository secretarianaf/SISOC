# Elevación de Figma

Fuente: estilos locales del archivo [Nuevo DS SISOC](https://www.figma.com/design/BUiPDYtrg9gHGJj4ZfBCtt/Nuevo-DS-SISOC--copia-?node-id=22-2168), leídos por Plugin API el 2026-10-05. Cada estilo tiene tres sombras `DROP_SHADOW` visibles con color base `#1C1917` y opacidades 20%, 14% y 12%, en ese orden. En la tabla cada capa se expresa como `x/y/blur/spread` en píxeles.

| Estilo | Capa 20% | Capa 14% | Capa 12% |
| --- | --- | --- | --- |
| `shadow/01` | `0/2/1/-1` | `0/1/1/0` | `0/1/3/0` |
| `shadow/02` | `0/3/1/-2` | `0/2/2/0` | `0/1/5/0` |
| `shadow/03` | `0/3/3/-2` | `0/3/4/0` | `0/1/8/0` |
| `shadow/04` | `0/2/4/-1` | `0/4/5/0` | `0/1/10/0` |
| `shadow/05` | `0/3/5/-1` | `0/5/8/0` | `0/1/14/0` |
| `shadow/06` | `0/3/5/-1` | `0/6/10/0` | `0/1/18/0` |
| `shadow/07` | `0/4/5/-2` | `0/7/10/1` | `0/2/16/1` |
| `shadow/08` | `0/5/5/-3` | `0/8/10/1` | `0/3/14/2` |
| `shadow/09` | `0/5/6/-3` | `0/9/12/1` | `0/3/16/2` |
| `shadow/10` | `0/6/6/-3` | `0/10/14/1` | `0/4/18/3` |
| `shadow/11` | `0/6/7/-4` | `0/11/15/1` | `0/4/20/3` |
| `shadow/12` | `0/7/8/-4` | `0/12/17/2` | `0/5/22/4` |
| `shadow/13` | `0/7/8/-4` | `0/13/19/2` | `0/5/24/4` |
| `shadow/14` | `0/7/9/-4` | `0/14/21/2` | `0/5/26/4` |
| `shadow/15` | `0/8/9/-5` | `0/15/22/2` | `0/6/28/5` |
| `shadow/16` | `0/8/10/-5` | `0/16/24/2` | `0/6/30/5` |
| `shadow/17` | `0/8/11/-5` | `0/17/26/2` | `0/6/32/5` |
| `shadow/18` | `0/9/11/-5` | `0/18/28/2` | `0/7/34/6` |
| `shadow/19` | `0/9/12/-6` | `0/19/29/2` | `0/7/36/6` |
| `shadow/20` | `0/10/13/-6` | `0/20/31/3` | `0/8/38/7` |
| `shadow/21` | `0/10/13/-6` | `0/21/33/3` | `0/8/40/7` |
| `shadow/22` | `0/10/14/-6` | `0/22/35/3` | `0/8/42/7` |
| `shadow/23` | `0/11/14/-7` | `0/23/36/3` | `0/9/44/8` |
| `shadow/24` | `0/11/15/-7` | `0/24/38/3` | `0/9/46/8` |

Para CSS, cada capa se traslada a `0px ypx blurpx spreadpx rgba(28,25,23,alpha)` en el mismo orden. Conservar el nombre semántico de la sombra en el tema o variables CSS; elegir la elevación por el componente mostrado en Figma.
