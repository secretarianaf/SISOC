# Sets y variantes de Figma

Fuente: lectura directa de la [página Componentes](https://www.figma.com/design/BUiPDYtrg9gHGJj4ZfBCtt/Nuevo-DS-SISOC--copia-?node-id=28-12456) mediante Figma Plugin API, 2026-10-05. Hay 46 sets y 32 componentes principales individuales. Los nombres de ejes son los de Figma; no implican una API React ni comportamiento implementado.

| Set | Variantes | Ejes verificados |
| --- | ---: | --- |
| `MUI/Button` | 90 | `Size`: Small / Large; `Variant`: Contained / Outlined / Text; `Color`: Primary / Secondary / Error; `State`: Enabled / Hovered / Focused / Pressed / Disabled |
| `Sisoc/Navigation card` | 5 | `State`: Enabled / Hovered / Focused / Pressed / Disabled |
| `Sisoc/Filter chip` | 10 | `Style`: Filled / Outlined; `State`: Enabled / Hover / Focused / Disabled / Selected |
| `MUI/Alert` | 12 | `Severity`: Error / Warning / Info / Success; `Variant`: Filled / Outlined / Standard |
| `MUI/Circular progress` | 3 | `STATE`: Incumplido / Parcial / Cumplido |
| `Sisoc/Alert message` | 3 | `STATE`: Parcial / Cumplido / Incumplido |
| `Sisoc/State chip` | 6 | `Color`: Primary / Success / Error / Warning / Neutral / Info |
| `Sisoc/Titular card` | 5 | `STATE`: Enabled / Hovered / Focused / Pressed / Disabled |
| `Sisoc/Score chip` | 3 | `Color`: Error / Warning / Success |
| `MUI/Linear progress` | 11 | `Progress`: 0 / 10 / 20 / 30 / 40 / 50 / 60 / 70 / 80 / 90 / 100 |
| `MUI/Timeline item` | 3 | `State`: Completed / Current / Pending |
| `MUI/Tab` | 4 | `State`: Default / Hover / Selected / Disabled |
| `Sisoc/Tabs Panel` | 3 | `TAB`: Datos personales / FCH / Historial de estados |
| `Sisoc/Ticket card` | 5 | `STATE`: Enabled / Hovered / Focused / Pressed / Disabled |
| `Sisoc/Priority label` | 3 | `Priority`: Alta / Media / Baja |
| `Sisoc/Scoring card` | 5 | `STATE`: Enabled / Hovered / Focused / Pressed / Disabled |
| `MUI/Avatar` | 9 | `Size`: 24px / 32px / 40px; `Content`: Image / Text / Icon |
| `Sisoc/Stat card` | 5 | `Color`: Primary / Secondary / Error / Warning / Success |
| `MUI/Link` | 4 | `State`: Default / Hover / Pressed / Disabled |
| `MUI/Step` | 3 | `State`: Completed / Active / Pending |
| `Sisoc/Monthly circuit stepper` | 7 | `Step`: 1 / 2 / 3 / 4 / 5 / 6 / Completo |
| `MUI/List item` | 27 | `Level`: 1 / 2 / 3; `State`: Default / Hover / Selected; `Caret`: Collapsed / Expanded / None |
| `MUI/IconButton` | 40 | `Size`: Small / Large; `Color`: Default / Primary / Secondary / Error; `State`: Enabled / Hovered / Focused / Pressed / Disabled |
| `MUI/Checkbox` | 9 | `Checked`: Unchecked / Checked / Indeterminate; `State`: Enabled / Hover / Disabled |
| `Sisoc/Program card` | 4 | `State`: Unselected / Hovered / Selected / Disabled |
| `Sisoc/Program icon` | 2 | `Size`: Medium / Large |
| `Sisoc/Module card` | 2 | `State`: Default / Hover |
| `Sisoc/Socioeconomic panel` | 3 | `Page`: 1 / 2 / 3 |
| `Sisoc/Family row` | 2 | `Type`: Head / Body |
| `Sisoc/Transfer card` | 5 | `Series`: 1 / 2 / 3 / 4 / 5 |
| `Sisoc/Chart segment` | 5 | `Series`: 1 / 2 / 3 / 4 / 5 |
| `Sisoc/Program panel` | 4 | `Program`: PAS / Prestación Alimentar / Situación de Calle / Ver para ser libres |
| `Sisoc/Personal data panel` | 2 | `Deceased`: False / True |
| `Sisoc/CFP row` | 2 | `Type`: Head / Body |
| `Sisoc/Applied filter` | 3 | `State`: Enabled / Hover / Editing |
| `Sisoc/Course row` | 2 | `Type`: Head / Body |
| `Sisoc/Commission row` | 2 | `Type`: Head / Body |
| `Sisoc/Location row` | 2 | `Type`: Head / Body |
| `Sisoc/Contact row` | 2 | `Type`: Head / Body |
| `MUI/FormHelperText` | 2 | `Variant`: Default / Error |
| `MUI/Text field` | 2 | `Content`: Placeholder / Value |
| `Sisoc/Enrollee row` | 2 | `Type`: Head / Body |
| `Sisoc/Class row` | 4 | `Type`: Head / Completada / Asistencia pendiente / Programada |
| `Sisoc/Attendance row` | 2 | `Type`: Head / Body |
| `MUI/Radio` | 6 | `Checked`: Unchecked / Checked; `State`: Enabled / Hover / Disabled |
| `MUI/Snackbar` | 2 | `State`: Open / Closed |

## Propiedades editables adicionales

Estos nombres pertenecen a Figma; requieren mapeo deliberado a las props reales del componente en código.

| Set | Propiedades de Figma |
| --- | --- |
| `MUI/Button` | `Start Icon#15487:0` (BOOLEAN), `Icon Choice#15494:0` (INSTANCE_SWAP) |
| `Sisoc/Navigation card` | `Number#426:0` (TEXT), `Title#426:6` (TEXT), `Subtitle#426:12` (TEXT), `Alert count#426:18` (TEXT), `Alert badge#426:24` (BOOLEAN) |
| `Sisoc/Filter chip` | `Label#15468:0` (TEXT) |
| `MUI/Alert` | `Overline?#150:0` (BOOLEAN), `↳ Overline#150:13` (TEXT), `On Close?#9972:0` (BOOLEAN), `Action?#9974:202` (BOOLEAN), `Description?#9989:17` (BOOLEAN), `Title?#9989:26` (BOOLEAN), `↳ Title#11069:1763` (TEXT), `↳ Description#11069:1772` (TEXT) |
| `Sisoc/State chip` | `Label#198:0` (TEXT), `Dot#15399:0` (BOOLEAN) |
| `Sisoc/Score chip` | `Label#222:0` (TEXT) |
| `MUI/Timeline item` | `Date#236:0` (TEXT), `Description#236:4` (TEXT) |
| `MUI/Tab` | `Label#241:10` (TEXT), `Icon#241:15` (BOOLEAN) |
| `MUI/Avatar` | `Initials#15791:0` (TEXT), `Badge#15791:10` (BOOLEAN) |
| `Sisoc/Stat card` | `Overline#356:3` (TEXT), `Value#356:4` (TEXT), `Reference#356:5` (TEXT) |
| `MUI/Link` | `Label#365:0` (TEXT) |
| `MUI/Step` | `Number#370:0` (TEXT), `Label#370:4` (TEXT), `Status#370:8` (TEXT), `Connector#370:12` (BOOLEAN) |
| `MUI/List item` | `Label#373:0` (TEXT), `Icon#373:10` (BOOLEAN), `Icon source#388:28` (INSTANCE_SWAP) |
| `MUI/IconButton` | `Icon source#412:0` (INSTANCE_SWAP) |
| `Sisoc/Program card` | `Title#481:0` (TEXT), `Subtitle#481:5` (TEXT), `Activity#481:10` (TEXT), `Icon source#481:15` (INSTANCE_SWAP) |
| `Sisoc/Program icon` | `Icon source#782:0` (INSTANCE_SWAP) |
| `Sisoc/Module card` | `Title#782:3` (TEXT), `Subtitle#782:6` (TEXT), `Tasks#782:9` (TEXT), `Activity#782:12` (TEXT) |
| `Sisoc/Family row` | `Nombre#882:0` (TEXT), `Apellido#882:3` (TEXT), `Parentesco#882:6` (TEXT), `Género#882:9` (TEXT), `Edad#882:12` (TEXT) |
| `Sisoc/Transfer card` | `Program#882:15` (TEXT), `Amount#882:21` (TEXT), `Icon source#882:27` (INSTANCE_SWAP) |
| `Sisoc/Personal data panel` | `Updated#903:0` (TEXT) |
| `Sisoc/CFP row` | `Nombre#961:0` (TEXT), `Provincia#961:3` (TEXT), `CUE#961:6` (TEXT), `Localidad#968:0` (TEXT) |
| `Sisoc/Applied filter` | `Field#966:2` (TEXT), `Value#966:6` (TEXT) |
| `Sisoc/Course row` | `Plan curricular#983:0` (TEXT), `Curso#983:3` (TEXT), `Comisiones#983:6` (TEXT) |
| `Sisoc/Commission row` | `Curso#983:9` (TEXT), `Comisión#983:12` (TEXT), `Ubicación#983:15` (TEXT), `Inicio#983:18` (TEXT), `Fin#983:21` (TEXT), `Cupo#983:24` (TEXT) |
| `Sisoc/Location row` | `Nombre#993:0` (TEXT), `Característica#993:3` (TEXT), `Localidad#993:6` (TEXT), `Domicilio#993:9` (TEXT) |
| `Sisoc/Contact row` | `Nombre y apellido#993:12` (TEXT), `Documento#993:15` (TEXT), `Rol#993:18` (TEXT), `Principal#993:21` (TEXT), `Teléfono#993:24` (TEXT) |
| `MUI/FormHelperText` | `Text#1004:2` (TEXT) |
| `MUI/Text field` | `Placeholder#1004:6` (TEXT), `Icon source#1004:7` (INSTANCE_SWAP), `Label#1004:8` (BOOLEAN), `Label text#1004:9` (TEXT), `Start icon#1005:0` (BOOLEAN) |
| `Sisoc/Enrollee row` | `Apellido y nombre#1010:0` (TEXT), `Documento#1010:6` (TEXT), `Email#1010:9` (TEXT), `Teléfono#1010:12` (TEXT), `Asistencia#1010:15` (TEXT) |
| `Sisoc/Class row` | `Clase#1010:18` (TEXT), `Fecha#1010:23` (TEXT), `Horario#1010:28` (TEXT), `Presentes#1010:33` (TEXT), `Ausentes#1010:38` (TEXT) |
| `Sisoc/Attendance row` | `Apellido y nombre#1010:43` (TEXT), `Documento#1010:46` (TEXT) |

## Iconos como componentes individuales

`MUI/Icon/Star`, `MUI/Icon/ArrowUpward`, `MUI/Icon/ArrowDownward`, `MUI/Icon/Add`, `MUI/Icon/Remove`, `MUI/Icon/Check`, `MUI/Icon/Close`, `MUI/Icon/Search`, `MUI/Icon/Delete`, `MUI/Icon/Edit`, `MUI/Icon/Home`, `MUI/Icon/Settings`, `MUI/Icon/Favorite`, `MUI/Icon/Send`, `MUI/Icon/Visibility`, `MUI/Icon/Refresh`, `MUI/Icon/ErrorOutline`, `MUI/Icon/WarningAmber`, `MUI/Icon/InfoOutlined`, `MUI/Icon/TaskAlt`, `MUI/Icon/ChevronRight`, `MUI/Icon/ExpandMore`, `MUI/Icon/Logout`, `MUI/Icon/Dashboard`, `MUI/Icon/Apps`, `MUI/Icon/Person`, `MUI/Icon/Lock`, `Sisoc/Icon/Home`, `Sisoc/Icon/FamilyShield`, `Sisoc/Icon/Eyeglasses`, `MUI/Icon/FileCopy`, `MUI/Icon/Restaurant`, `MUI/Icon/LocationOn`, `MUI/Icon/SubdirectoryArrowRight`, `MUI/Icon/DarkModeOutlined`, `MUI/Icon/ArrowForward`, `MUI/Icon/ArrowBack`, `MUI/Icon/Download`, `MUI/Icon/ChevronLeft`, `MUI/Icon/EscalatorWarning`, `MUI/Icon/Inventory2`, `MUI/Icon/History`, `MUI/Icon/ArrowDropDown`, `MUI/Icon/Cancel`, `MUI/Icon/School`, `MUI/Icon/CalendarToday`, `MUI/Icon/Schedule`, `MUI/Icon/PersonRemove`.

Los componentes con propiedades editables adicionales incluyen texto, visibilidad booleana e intercambio de iconos. Inspeccionar el set concreto antes de conectar props en código.
