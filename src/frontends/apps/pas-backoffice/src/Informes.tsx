import { Alert, Box, Button, Card, MenuItem, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { generarInforme, pasGet, pasPost, type Informe } from "./api";
import { Cargando, ErrorPas } from "./Estado";
import { ErrorOperacion } from "./Gestion";

type Columna = { key: string; label: string };
type Detalle = Informe & { total_cambios: number; filtros: { clave: string; valor: string }[]; columns: Columna[]; rows: string[][] };
type Opcion = { id: number; nombre: string };
type Opciones = { estados: Opcion[]; avisos: { id: number; texto: string }[]; provincias: Opcion[]; municipios: Opcion[] };
type VistaPrevia = { total: number; columns: Columna[]; rows: Record<string, unknown>[] };

function TablaInforme({ columns, rows }: { columns: Columna[]; rows: string[][] }) {
  return <TableContainer component={Card} variant="outlined">
    <Table size="small" aria-label="Resultados del informe">
      <TableHead><TableRow>{columns.map(({ key, label }) => <TableCell key={key}>{label}</TableCell>)}</TableRow></TableHead>
      <TableBody>
        {rows.length === 0 && <TableRow><TableCell colSpan={columns.length || 1}>Sin resultados.</TableCell></TableRow>}
        {rows.map((row, index) => <TableRow key={index}>{row.map((valor, columna) => <TableCell key={columna}>{valor}</TableCell>)}</TableRow>)}
      </TableBody>
    </Table>
  </TableContainer>;
}

export function InformeDetallePage() {
  const { id } = useParams();
  const path = `informes/${id}/`;
  const query = useQuery({ queryKey: ["pas", path], queryFn: () => pasGet<Detalle>(path) });
  if (query.isPending) return <Cargando />;
  if (query.isError) return <ErrorPas error={query.error} />;
  const data = query.data;
  return <Stack spacing={2}>
    <Typography component="h1" variant="h5">Informe {data.numero}</Typography>
    <Typography>{data.creado} · Personas: {data.total_personas} · Cambios: {data.total_cambios}</Typography>
    {data.filtros.length > 0 && <Stack component="ul" sx={{ pl: 3 }}>
      {data.filtros.map(({ clave, valor }) => <li key={clave}>{clave}: {valor}</li>)}
    </Stack>}
    <Stack direction="row" spacing={2}>
      <Button component={Link} to="/informes">Volver a informes</Button>
      {data.download_url && <Button variant="outlined" href={data.download_url}>Descargar CSV</Button>}
    </Stack>
    <TablaInforme columns={data.columns} rows={data.rows} />
  </Stack>;
}

const fechas = [
  ["fecha_creacion_desde", "Fecha de alta desde"], ["fecha_creacion_hasta", "Fecha de alta hasta"],
  ["fecha_cambio_desde", "Fecha de cambio desde"], ["fecha_cambio_hasta", "Fecha de cambio hasta"],
];
const estados = [["estado_anterior", "Estado anterior"], ["estado_nuevo", "Estado resultante"], ["estado_actual", "Estado actual"]];
const avisos = [["aviso_cambio", "Aviso del cambio"], ["aviso_actual", "Aviso actual"]];

function Selector({ name, label, options }: { name: string; label: string; options: Opcion[] }) {
  return <TextField select name={name} label={label} defaultValue="">
    <MenuItem value="">Todos</MenuItem>
    {options.map(({ id, nombre }) => <MenuItem key={id} value={id}>{nombre}</MenuItem>)}
  </TextField>;
}

export function InformeGenerarPage() {
  const [provincia, setProvincia] = useState("");
  const [vista, setVista] = useState<VistaPrevia | null>(null);
  const form = useRef<HTMLFormElement>(null);
  const cache = useQueryClient();
  const base = useQuery({ queryKey: ["pas", "opciones-informe"], queryFn: () => pasGet<Opciones>("informes/opciones/") });
  const local = useQuery({
    queryKey: ["pas", "opciones-informe", provincia],
    queryFn: () => pasGet<Opciones>(`informes/opciones/?${new URLSearchParams({ provincia })}`),
    enabled: Boolean(provincia),
  });
  const accion = useMutation({
    mutationFn: async ({ tipo, values }: { tipo: "previa" | "generar"; values: FormData }) => tipo === "previa"
      ? { vista: await pasPost<VistaPrevia>("informes/previsualizar/", values) }
      : { id: await generarInforme(values) },
    onSuccess: async (resultado) => {
      if (resultado.vista) setVista(resultado.vista);
      else await cache.invalidateQueries({ queryKey: ["pas"] });
    },
  });
  if (base.isPending) return <Cargando />;
  if (base.isError) return <ErrorPas error={base.error} />;
  const opciones = base.data;
  function ejecutar(tipo: "previa" | "generar") {
    if (!form.current || accion.isPending) return;
    setVista(null);
    accion.mutate({ tipo, values: new FormData(form.current) });
  }
  return <Stack spacing={2}>
    <Typography component="h1" variant="h5">Generar informe PAS</Typography>
    {accion.isError && <ErrorOperacion error={accion.error} />}
    {accion.isSuccess && "id" in accion.data && <Alert severity="success">Informe generado. Se inició la descarga del CSV.</Alert>}
    <Stack spacing={2} component="form" ref={form} onSubmit={(event) => { event.preventDefault(); ejecutar("generar"); }}>
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(2,minmax(0,1fr))", lg: "repeat(4,minmax(0,1fr))" } }}>
        {fechas.map(([name, label]) => <TextField key={name} name={name} label={label} type="date" slotProps={{ inputLabel: { shrink: true } }} />)}
        {estados.map(([name, label]) => <Selector key={name} name={name} label={label} options={opciones.estados} />)}
        {avisos.map(([name, label]) => <Selector key={name} name={name} label={label}
          options={opciones.avisos.map(({ id, texto }) => ({ id, nombre: texto }))} />)}
        <TextField select name="provincia" label="Provincia" value={provincia} onChange={(event) => setProvincia(event.target.value)}>
          <MenuItem value="">Todas</MenuItem>
          {opciones.provincias.map(({ id, nombre }) => <MenuItem key={id} value={String(id)}>{nombre}</MenuItem>)}
        </TextField>
        <Selector key={provincia} name="municipio" label="Municipio" options={local.data?.municipios ?? []} />
        <TextField name="dni" label="DNI" />
        <TextField name="id_persona" label="IdPersona" />
        <TextField name="usuario_cambio" label="Usuario que modificó" />
      </Box>
      {local.isError && <ErrorPas error={local.error} />}
      <Stack direction="row" spacing={2} useFlexGap sx={{ flexWrap: "wrap" }}>
        <Button component={Link} to="/informes">Cancelar</Button>
        <Button type="button" variant="outlined" disabled={accion.isPending} onClick={() => ejecutar("previa")}>Previsualizar</Button>
        <Button type="submit" variant="contained" disabled={accion.isPending}>Generar y descargar CSV</Button>
      </Stack>
    </Stack>
    {vista && <>
      <Alert severity="info">Resultados de la vista previa: {vista.total}</Alert>
      <TablaInforme columns={vista.columns} rows={vista.rows.map((row) => vista.columns.map(({ key }) => String(row[key] ?? "")))} />
    </>}
  </Stack>;
}
