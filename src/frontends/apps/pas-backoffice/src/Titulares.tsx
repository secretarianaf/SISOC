import { Alert, alpha, Box, Button, ButtonBase, Card, Chip, IconButton, InputAdornment, MenuItem, Stack, Tab, Tabs, TextField, Tooltip, Typography } from "@mui/material";
import ChevronLeft from "@mui/icons-material/ChevronLeft";
import ChevronRight from "@mui/icons-material/ChevronRight";
import Download from "@mui/icons-material/Download";
import Search from "@mui/icons-material/Search";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { exportarTokens, pasGet, type Ficha, type Padron, type Titular } from "./api";
import { AccionesPas } from "./AccionesPas";
import { DataGroup, EstadoChip, Oculto, StateChip, TablaCursos } from "./componentes";
import { CambiarEstado } from "./Gestion";
import { Cargando, ErrorPas } from "./Estado";

/** Provincia de la tarjeta; la Ciudad Autónoma de Buenos Aires se abrevia CABA. */
function nombreProvincia(provincia: string) {
  if (!provincia) return "—";
  const normalizada = provincia.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  return normalizada.includes("ciudad autonoma de buenos aires") ? "CABA" : provincia;
}

/** `Sisoc/Titular card`: ButtonBase con chips de display. La provincia va en FILL. */
function TitularCard({ persona, selected, to }: { persona: Titular; selected: boolean; to: string }) {
  return <ButtonBase component={Link} to={to} aria-current={selected ? "true" : undefined}
    sx={(theme) => ({ display: "block", width: "100%", p: 2, textAlign: "left", border: 1, borderRadius: `${theme.radius.large}px`,
      borderColor: selected ? "primary.main" : "divider", bgcolor: selected ? alpha(theme.palette.primary.main, 0.08) : "background.paper",
      "&:hover": { bgcolor: alpha(theme.palette.primary.main, selected ? 0.12 : 0.04) },
      "&.Mui-focusVisible": { outline: `${theme.border.focus}px solid ${theme.palette.primary.main}`, outlineOffset: 2 } })}>
    <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "start" }}>
      <Typography variant="subtitle2" component="span">
        <Box component="span" sx={{ textTransform: "uppercase" }}>{persona.apellidos}</Box>, {persona.nombres}
      </Typography>
      <Box sx={{ flexShrink: 0 }}><EstadoChip nombre={persona.estado.nombre} /></Box>
    </Stack>
    <Typography variant="caption" component="p">{persona.cuit || `DNI ${persona.dni}`}</Typography>
    <Stack direction="row" spacing={1} sx={{ pt: 1, justifyContent: "space-between", alignItems: "center" }}>
      <Typography variant="caption" component="p" sx={{ minWidth: 0 }}>{nombreProvincia(persona.provincia)}</Typography>
      {(persona.tag_ddjj || persona.tag_fch) && <Stack direction="row" spacing={0.5} sx={{ flexShrink: 0 }}>
        {persona.tag_ddjj && <PendienteChip label="DDJJ" titulo="DDJJ sin completar" />}
        {persona.tag_fch && <PendienteChip label="FCH" titulo="Formación FCH bajo 100 puntos" />}
      </Stack>}
    </Stack>
  </ButtonBase>;
}

/** Chip de pendiente de la `Sisoc/Titular card` (Figma): borde ámbar, capa ámbar suave y caption. */
function PendienteChip({ label, titulo }: { label: string; titulo: string }) {
  return <Box component="span" title={titulo} aria-label={titulo} sx={(theme) => ({ display: "inline-block", px: 0.75, border: 1,
    borderColor: "warning.main", borderRadius: `${theme.radius.base}px`, bgcolor: alpha(theme.palette.warning.main, 0.12),
    color: "text.primary", typography: "caption", lineHeight: "20px" })}>{label}</Box>;
}

export function PadronPage() {
  const { id } = useParams();
  const [params, setParams] = useSearchParams();
  const query = useQuery({ queryKey: ["pas", "padron", params.toString()], queryFn: () => pasGet<Padron>(`personas/?${params}`) });
  const tokens = useMutation({ mutationFn: exportarTokens });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const data = query.data;
  const selected = id ?? (data.results[0] ? String(data.results[0].id) : undefined);
  function go(page: number | null) {
    if (page === null) return;
    const next = new URLSearchParams(params);
    next.set("page", String(page));
    setParams(next);
  }
  return <Box sx={{ display: "grid", gap: 3, alignItems: "stretch", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(240px, 296px) minmax(0, 1fr)" } }}>
    <Stack component="aside" aria-label="Padrón de titulares" spacing={1.5} sx={{ minWidth: 0 }}>
      <Oculto component="h1">Titulares PAS</Oculto>
      <Box component="form" role="search" key={params.toString()} onSubmit={(event) => {
        event.preventDefault();
        const fields = new FormData(event.currentTarget as HTMLFormElement);
        setParams({ q: String(fields.get("q") ?? "").trim(), estado: params.get("estado") ?? "" });
      }}>
        <TextField name="q" type="search" placeholder="Buscar…" defaultValue={params.get("q") ?? ""} fullWidth
          slotProps={{ htmlInput: { "aria-label": "Buscar titular" }, input: {
            startAdornment: <InputAdornment position="start"><Search sx={{ color: "action.active" }} /></InputAdornment>,
            endAdornment: <InputAdornment position="end"><AccionesPas label="Acciones del padrón" items={[
              ...(data.capabilities.can_import ? [{ label: "Nuevo titular", to: "/titulares/nuevo" }, { label: "Importar titulares", to: "/titulares/importar" }] : []),
              ...(data.capabilities.can_export_tokens ? [{ label: "Exportar tokens", disabled: tokens.isPending, run: () => tokens.mutate() }] : []),
              { label: "Abrir Buscador PAS", to: "/buscador" },
            ]} /></InputAdornment> } }} />
      </Box>
      {tokens.isError && <Alert severity="error" onClose={() => tokens.reset()}>No se pudieron exportar los tokens.</Alert>}
      <Stack direction="row" useFlexGap sx={{ flexWrap: "wrap", columnGap: 2.5, rowGap: 0.75 }} role="group" aria-label="Estado">
        {["", ...data.estados.map(({ nombre }) => nombre)].map((estado) => {
          const active = (params.get("estado") ?? "") === estado;
          return <Chip key={estado} label={estado || "Todos"} color={active ? "primary" : "default"}
            aria-pressed={active} onClick={() => setParams({ q: params.get("q") ?? "", estado })} />;
        })}
      </Stack>
      <Stack spacing={1.25} sx={{ maxHeight: { md: 542 }, overflowY: "auto", pr: 0.5 }}>
        {data.results.length === 0 && <Alert severity="info">Sin titulares para los filtros seleccionados.</Alert>}
        {data.results.map((persona) => <TitularCard key={persona.id} persona={persona} selected={selected === String(persona.id)}
          to={`/titulares/${persona.id}?${params}`} />)}
      </Stack>
      <Stack direction="row" spacing={0.5} sx={{ justifyContent: "center", alignItems: "center", pt: 0.5, borderTop: 1, borderColor: "divider" }}>
        <Tooltip title="Página anterior"><span><IconButton size="small" aria-label="Página anterior" disabled={data.previous === null} onClick={() => go(data.previous)}><ChevronLeft /></IconButton></span></Tooltip>
        <Typography variant="caption" color="text.secondary">{data.total_padron} {data.total_padron === 1 ? "titular" : "titulares"} · Padrón al {new Date().toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })}</Typography>
        <Tooltip title="Página siguiente"><span><IconButton size="small" aria-label="Página siguiente" disabled={data.next === null} onClick={() => go(data.next)}><ChevronRight /></IconButton></span></Tooltip>
      </Stack>
    </Stack>
    {selected ? <FichaPage key={selected} id={selected} /> : <Card sx={{ p: 4, minHeight: { md: 620 } }}>
      <Typography variant="h6">Ficha del titular</Typography>
      <Typography color="text.secondary">Seleccioná un titular del padrón para consultar su ficha.</Typography>
    </Card>}
  </Box>;
}

/** Orden de cada grupo de la DDJJ, como en Figma. `domicilio` une calle y altura. */
const ordenContacto = ["domicilio", "municipio", "provincia", "telefono_celular", "correo_electronico", "datos_mi_argentina_confirmados"];
const ordenSalud = ["embarazada", "controles_embarazo_cumplidos", "vacunacion_cumplida", "hijos_menores_a_cargo", "regularidad_escolar_acreditada"];
const ordenConsumos = ["gastos_bajo_limite_smvm", "no_accedio_mercado_cambios"];

/** Declaración jurada: Data field en tres grupos por periodicidad de la DDJJ. */
function RespuestasDDJJ({ respuestas }: { respuestas: NonNullable<Ficha["ddjj"]["seleccionada"]>["respuestas"] }) {
  const porClave = new Map(respuestas.map((fila) => [fila.clave, fila]));
  const calle = porClave.get("calle")?.respuesta;
  const altura = porClave.get("altura")?.respuesta;
  if (calle || altura) porClave.set("domicilio", { clave: "domicilio", etiqueta: "Domicilio", respuesta: [calle, altura].filter(Boolean).join(" ") });
  const usadas = new Set(["calle", "altura", ...ordenContacto, ...ordenSalud, ...ordenConsumos]);
  const tomar = (orden: string[]) => orden.flatMap((clave) => { const fila = porClave.get(clave); return fila ? [fila] : []; });
  // Una respuesta que no esté en el orden de Figma no se pierde: va al final de Contacto.
  const otras = respuestas.filter(({ clave }) => !usadas.has(clave));
  const grupos = [
    { titulo: "Contacto y domicilio", filas: [...tomar(ordenContacto), ...otras] },
    { titulo: "Salud y educación · anual", filas: tomar(ordenSalud) },
    { titulo: "Consumos y divisas · semestral", filas: tomar(ordenConsumos) },
  ];
  return <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" } }}>
    {grupos.filter(({ filas }) => filas.length > 0).map(({ titulo, filas }) => <DataGroup key={titulo} titulo={titulo}
      campos={filas.map(({ etiqueta, respuesta }): [string, string] => [etiqueta, respuesta])} />)}
  </Box>;
}

const pestanas = ["Datos personales", "Capacitaciones FCH", "Declaración jurada", "Historial de datos"];

/** Un Data field suelto: etiqueta caption y valor subtitle2, sin dato con guión largo. */
function Dato({ label, valor }: { label: string; valor?: string | number | null }) {
  return <div>
    <Typography component="dt" variant="caption" color="text.secondary">{label}</Typography>
    <Typography component="dd" variant="subtitle2" sx={{ m: 0, overflowWrap: "anywhere" }}>{valor === "" || valor == null ? "—" : valor}</Typography>
  </div>;
}

/**
 * Datos personales, como en Figma: "Datos del Titular" y tres columnas sin
 * título (Identidad, Contacto, Domicilio), y debajo Información Financiera.
 * Fecha de nacimiento, teléfono fijo y los datos financieros no tienen fuente
 * en PAS todavía: se muestran con guión largo.
 */
function DatosTitular({ persona }: { persona: NonNullable<Ficha["persona"]> }) {
  const columnas: [string, [string, string | number | undefined][]][] = [
    ["Identidad", [["DNI", persona.dni ? persona.dni.toLocaleString("es-AR") : undefined], ["Fecha de nacimiento", undefined]]],
    ["Contacto", [["Teléfono", undefined], ["Celular", persona.telefono_celular], ["Email", persona.correo_electronico]]],
    ["Domicilio", [["Provincia", persona.provincia], ["Municipio / Localidad", persona.municipio], ["Domicilio", persona.domicilio]]],
  ];
  return <Stack spacing={3}>
    <section aria-labelledby="datos-titular">
      <Typography id="datos-titular" component="h3" variant="overline" color="text.primary" sx={{ display: "block" }}>Datos del Titular</Typography>
      <Box sx={{ mt: 2.5, display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" } }}>
        {columnas.map(([grupo, campos]) => <Stack key={grupo} component="dl" spacing={1} aria-label={grupo} sx={{ m: 0, minWidth: 0 }}>
          {campos.map(([label, valor]) => <Dato key={label} label={label} valor={valor} />)}
        </Stack>)}
      </Box>
    </section>
    <Box component="section" aria-labelledby="info-financiera" sx={(theme) => ({ p: 3, borderRadius: `${theme.radius.medium}px`, bgcolor: "action.hover" })}>
      <Typography id="info-financiera" component="h3" variant="overline" color="text.primary" sx={{ display: "block" }}>Información Financiera</Typography>
      <Box component="dl" sx={{ m: 0, mt: 2.5, display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" } }}>
        <div>
          <Typography component="dt" variant="caption" color="text.secondary">Asignación mensual</Typography>
          <Typography component="dd" variant="h4Bold" sx={{ m: 0 }}>—</Typography>
        </div>
        <Dato label="CBU / Cuenta BNA" />
        <Dato label="Estado de cuenta" />
      </Box>
    </Box>
  </Stack>;
}

/**
 * Historial, como el `MUI/Timeline item` de Figma (con Box y Stack, sin `@mui/lab`):
 * orden cronológico, punto de 12px y conector de 2px en `primary.main`; el
 * evento actual (el último) lleva el anillo en `primary.light`.
 */
function Historial({ eventos }: { eventos: Ficha["eventos_historial"] }) {
  if (!eventos.length) return <Alert severity="info">Sin cambios registrados.</Alert>;
  // El backend los manda del más nuevo al más viejo.
  const cronologico = [...eventos].reverse();
  return <Box sx={{ p: 0.5, maxWidth: 470 }}>
    <Typography component="h3" variant="overline" color="text.secondary" sx={{ display: "block" }}>Línea de tiempo cronológica</Typography>
    <Box component="ol" sx={{ listStyle: "none", m: 0, p: 0 }}>
      {cronologico.map((evento, i) => {
        const actual = i === cronologico.length - 1;
        return <Stack component="li" key={i} direction="row" spacing={1.5} sx={{ minHeight: 64 }}>
          <Stack spacing={0.5} sx={{ alignItems: "center", width: 12, flexShrink: 0 }} aria-hidden="true">
            <Box sx={(theme) => ({ width: 12, height: 12, borderRadius: "50%", bgcolor: "primary.main",
              boxShadow: actual ? `0 0 0 2px ${theme.palette.primary.light}` : "none" })} />
            {!actual && <Box sx={{ width: 2, flex: 1, borderRadius: 9999, bgcolor: "primary.main" }} />}
          </Stack>
          <Box sx={{ pb: 2, mt: "-4px" }}>
            <Typography variant="body2">{evento.fecha}</Typography>
            <Typography variant="body2">{evento.estado ?? `Declaración jurada${evento.version ? ` · Versión ${evento.version}` : ""}`}</Typography>
            {evento.observacion && <Typography variant="caption" component="p" color="text.secondary">{evento.observacion}</Typography>}
          </Box>
        </Stack>;
      })}
    </Box>
  </Box>;
}

/** `Sisoc/Tabs Panel`: ficha del titular con cuatro pestañas. */
function FichaPage({ id }: { id: string }) {
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState(0);
  const [cambioAbierto, setCambioAbierto] = useState(false);
  const ddjj = params.get("ddjj");
  const endpoint = `panel/${id}/${ddjj ? `?${new URLSearchParams({ ddjj })}` : ""}`;
  const query = useQuery({ queryKey: ["pas", endpoint], queryFn: () => pasGet<Ficha>(endpoint) });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const { persona, formaciones, ddjj: declaraciones, eventos_historial } = query.data;
  if (!persona) return <Alert severity="info">Sin titular seleccionado.</Alert>;
  return <Card sx={{ minWidth: 0, minHeight: { md: 620 }, p: { xs: 2, md: 4 } }}>
    <Stack spacing={2} sx={{ pt: 2, pb: 3 }}>
      <Stack direction="row" spacing={1} sx={{ justifyContent: "space-between", alignItems: "start" }}>
        <Typography component="h2" variant="h4">{persona.apellidos}, {persona.nombres}</Typography>
        <AccionesPas label="Acciones del titular" items={[
          ...(query.data.capabilities?.can_change ? [
            { label: "Editar datos personales", to: `/titulares/${id}/editar` },
            ...(query.data.cambio_estado ? [{ label: "Cambiar estado", run: () => setCambioAbierto(true) }] : []),
          ] : []),
          { label: "Ver Formación del titular", to: `/formacion?persona=${id}` },
          ...(query.data.capabilities?.can_delete ? [{ label: "Eliminar titular", href: `/pas/${persona.id}/eliminar` }] : []),
        ]} />
      </Stack>
      <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap", alignItems: "center" }}>
        <Typography variant="body2">{persona.cuit || `DNI ${persona.dni}`}</Typography>
        <EstadoChip nombre={persona.estado.nombre} />
        {persona.avisos.map((aviso) => <StateChip key={aviso.codigo} label={aviso.descripcion} />)}
      </Stack>
      {query.data.capabilities?.can_change && query.data.cambio_estado && <CambiarEstado id={id}
        opciones={query.data.cambio_estado} open={cambioAbierto} onClose={() => setCambioAbierto(false)} />}
    </Stack>
    {/* En pantallas angostas (1366 px con el padrón al lado) las cuatro pestañas no entran:
        se achican y el texto pasa a dos líneas, en vez de esconderse detrás de una flecha. */}
    <Tabs value={tab} onChange={(_, value: number) => setTab(value)} aria-label="Ficha del titular"
      sx={{ "& .MuiTab-root": { flexShrink: 1, minWidth: 0, whiteSpace: "normal", lineHeight: 1.3 } }}>
      {pestanas.map((nombre, i) => <Tab key={nombre} label={nombre} id={`ficha-tab-${i}`} aria-controls="ficha-panel" />)}
    </Tabs>
    <Box role="tabpanel" id="ficha-panel" aria-labelledby={`ficha-tab-${tab}`} sx={{ pt: tab === 0 || tab === 2 ? 3 : 0.5 }}>
      {tab === 0 && <DatosTitular persona={persona} />}
      {tab === 1 && <TablaCursos key={id} rows={formaciones} titulo="Cursos registrados - Portal FCH" paginacion="auto" />}
      {tab === 2 && (declaraciones.seleccionada ? <Stack spacing={3}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { sm: "center" } }}>
          <TextField select label="Presentación consultada" value={ddjj ?? String(declaraciones.declaraciones[0]?.id ?? "")}
            onChange={(event) => { const next = new URLSearchParams(params); next.set("ddjj", event.target.value); setParams(next); }}
            sx={{ width: { xs: "100%", sm: 360 } }}>
            {declaraciones.declaraciones.map((item) => <MenuItem key={item.id} value={String(item.id)}>
              Versión {item.version} · {item.presentada}{item.es_ultima ? " · Última" : ""}
            </MenuItem>)}
          </TextField>
          <Button href={declaraciones.seleccionada.download_url} variant="outlined" size="small" startIcon={<Download />}
            sx={{ alignSelf: { xs: "start", sm: "center" } }}>Descargar PDF</Button>
        </Stack>
        <RespuestasDDJJ respuestas={declaraciones.seleccionada.respuestas} />
      </Stack> : <Alert severity="info">Sin declaraciones presentadas.</Alert>)}
      {tab === 3 && <Historial eventos={eventos_historial} />}
    </Box>
  </Card>;
}
