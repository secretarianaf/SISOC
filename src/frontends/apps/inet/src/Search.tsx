import { useState } from "react";
import { Alert, Box, Button, Chip, InputAdornment, MenuItem, Stack, TextField, Typography } from "@mui/material";
import ArrowBack from "@mui/icons-material/ArrowBack";
import Download from "@mui/icons-material/Download";
import SearchIcon from "@mui/icons-material/Search";
import Add from "@mui/icons-material/Add";
import { inetGet, mensajeDeError, type InetForm, type InetItem, type InetPage, type InetSession } from "@sisoc/api";
import { Field } from "./Fields";
import { queryString, useInet, type Resource } from "./data";
import { ResourceTable } from "./ResourceTable";
import { frames } from "./design";

type AppliedFilter = { name: string; value: unknown; label: string };
const labels: Record<string, string> = { nombre: "Nombre", cue: "CUE", provincia: "Provincia", localidad: "Localidad", activo: "Estado", sector: "Sector" };

export function SearchPage({ session, onEdit, onDelete, plans = false }: {
  session: InetSession; plans?: boolean;
  onEdit: (resource: Resource, item?: InetItem, initial?: Record<string, unknown>) => void;
  onDelete: (resource: Resource, item: InetItem) => void;
}) {
  const resource = plans ? "planes" : "centros";
  const schema = useInet<InetForm>(`${resource}/filter-form/`);
  const [applied, setApplied] = useState<AppliedFilter[]>([]);
  const [name, setName] = useState("nombre");
  const [valueLabel, setValueLabel] = useState("");
  const [value, setValue] = useState<unknown>("");
  const [editing, setEditing] = useState<string>();
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<unknown>();
  const filters = Object.fromEntries(applied.map((filter) => [filter.name === "nombre" && plans ? "search" : filter.name, filter.value]));
  const names = plans ? ["nombre", "provincia", "sector", "activo"] : ["nombre", "cue", "provincia", "localidad", "activo"];
  const available = names.filter((key) => key === editing || !applied.some((filter) => filter.name === key));
  const field = schema.data?.fields.find((entry) => entry.name === name);
  function reset(next: AppliedFilter[]) {
    setName(names.find((key) => !next.some((filter) => filter.name === key)) || "nombre");
    setValue(""); setValueLabel(""); setEditing(undefined);
  }
  function apply() {
    if (value === "" || value === null || value === undefined) return;
    const label = name === "activo" ? value === "true" ? "Activo" : "Inactivo" : valueLabel || field?.options.find((option) => option.value === String(value))?.label || String(value);
    const next = [...applied.filter((filter) => filter.name !== name && !(name === "provincia" && filter.name === "localidad")), { name, value, label }];
    setApplied(next); reset(next);
  }
  async function exportSearch() {
    setExporting(true); setError(undefined);
    try {
      const rows: InetItem[] = [];
      let page = 1;
      while (true) {
        const result = await inetGet<InetPage>(`${resource}/?${queryString({ ...filters, page, page_size: 200 })}`);
        rows.push(...result.results); if (!result.next) break; page++;
      }
      // Evitar fórmulas al abrir valores externos en una planilla.
      const cell = (input: unknown) => `"${String(input ?? "").replace(/^[=+@-]/, "'$&").replaceAll('"', '""')}"`;
      const csv = [plans ? ["Nombre", "Provincia", "Estado"] : ["Nombre", "Provincia", "Localidad", "CUE", "Estado"], ...rows.map((item) => plans ? [item.nombre, item.provincia, item.estado] : [item.nombre, item.provincia, item.localidad, item.cue, item.estado])].map((row) => row.map(cell).join(";")).join("\r\n");
      const url = URL.createObjectURL(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a"); link.href = url; link.download = `inet-${resource}.csv`; link.click(); URL.revokeObjectURL(url);
    } catch (failure) { setError(failure); } finally { setExporting(false); }
  }
  if (plans && !session.puede_ver_planes) return <Alert severity="error">No tenés permiso para administrar planes curriculares.</Alert>;
  return <Box data-figma-node={plans ? undefined : applied.length ? frames.searchFiltered : frames.search}>
    <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", mb: 4, gap: 2 }}>
      <Button variant="outlined" startIcon={<ArrowBack />} component="a" href="/" sx={{ color: "primary.text" }}>Volver</Button>
      <Button startIcon={<Download />} sx={{ color: "primary.text" }} disabled={exporting} onClick={() => void exportSearch()}>{exporting ? "Exportando…" : "Exportar búsqueda"}</Button>
    </Stack>
    <Typography variant="h4Bold" component="h1" sx={{ mb: 3 }}>{plans ? "Planes curriculares" : "Buscar Centro de Formación Profesional"}</Typography>
    <Box component="form" onSubmit={(event: React.FormEvent) => { event.preventDefault(); apply(); }} onKeyDown={(event) => { if (event.key === "Escape" && editing) reset(applied); }}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ alignItems: { md: "center" } }}>
        <TextField select label="Filtrar por" value={name} disabled={!available.length} onChange={(event) => { setName(event.target.value); setValue(""); setValueLabel(""); }} sx={{ width: { xs: "100%", md: 200 }, flexShrink: 0 }}>
          {(available.length ? available : [name]).map((key) => <MenuItem key={key} value={key}>{labels[key]}</MenuItem>)}
        </TextField>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {name === "activo" ? <TextField fullWidth select label="Estado" value={value} onChange={(event) => setValue(event.target.value)}><MenuItem value="true">Activo</MenuItem><MenuItem value="false">Inactivo</MenuItem></TextField>
            : field ? <Field field={{ ...field, required: false, label: labels[name], value }} value={value} values={filters} optionsPath={`${resource}/options/`} onChange={setValue} onOptionLabel={setValueLabel} />
            : <TextField fullWidth value={value} placeholder={name === "cue" ? "Escribí el CUE" : "Escribí parte del nombre"} slotProps={{ htmlInput: { "aria-label": `Valor del filtro ${labels[name]}` }, input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }} onChange={(event) => setValue(event.target.value)} />}
        </Box>
        <Button variant="outlined" type="submit" startIcon={<Add />} disabled={value === "" || !available.length} sx={{ flexShrink: 0 }}>{editing ? "Actualizar filtro" : "Agregar filtro"}</Button>
        {editing && <Button onClick={() => reset(applied)}>Cancelar</Button>}
      </Stack>
      {!applied.length ? <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>Sin filtros: se muestran todos los {plans ? "planes curriculares" : "CFP"}.</Typography>
        : <Stack direction="row" spacing={1} useFlexGap sx={{ mt: 2, flexWrap: "wrap", alignItems: "center" }}>{applied.map((filter) => <Chip key={filter.name} label={<><Box component="span" sx={{ color: "text.secondary" }}>{labels[filter.name]}:</Box> {filter.label}</>} aria-label={`${labels[filter.name]}: ${filter.label}`} onClick={() => { setEditing(filter.name); setName(filter.name); setValue(filter.value); setValueLabel(filter.label); }} onDelete={() => { const next = applied.filter((entry) => entry.name !== filter.name && !(filter.name === "provincia" && entry.name === "localidad")); setApplied(next); reset(next); }} />)}<Button onClick={() => { setApplied([]); reset([]); }}>Limpiar filtros</Button></Stack>}
    </Box>
    {schema.error && <Alert severity="error" sx={{ mt: 2 }}>{mensajeDeError(schema.error)}</Alert>}
    {!!error && <Alert severity="error" sx={{ mt: 2 }}>{mensajeDeError(error)}</Alert>}
    <Box sx={{ mt: 4 }}><ResourceTable key={JSON.stringify(filters)} resource={resource} filters={filters} session={session} onEdit={onEdit} onDelete={onDelete} presentation="search" /></Box>
  </Box>;
}
