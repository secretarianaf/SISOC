import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Alert, Box, Button, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { leerCookie } from "@sisoc/api";
import { internal, loadProjection } from "./transport";

export type Message = { level: string; text: string };

const srOnly = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" } as const;

type Provincia = { id: number; nombre: string };
type Totals = { candidatos: number; validados: number; excluidos: number };
type PagoRow = Totals & { id: number; periodo: string; estado: string; creado: string; url: string };
type PagosData = {
  version: number; provincia: Provincia; rows: PagoRow[];
  urls: { volver: string; crear: string }; messages: Message[];
};
type PagoDetalleData = {
  version: number;
  pago: Totals & { id: number; provincia: Provincia; periodo: string; estado: string };
  urls: { volver: string; archivo_envio: string | null; exportar_nomina: string };
  upload: { action: string; field: string; label: string; required: boolean };
  nomina: { documento: string; nombre: string; apellido: string; estado: string; observacion: string }[];
  messages: Message[];
};

/** Loads the projection of the current canonical URL and checks its contract version. */
export function useProjection<T extends { version: number; messages: Message[] }>(isValid: (data: T) => boolean) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    loadProjection<T>(undefined, controller.signal)
      .then((body) => {
        if (body?.version !== 1 || !Array.isArray(body.messages) || !isValid(body)) throw new Error("La pantalla no es compatible con esta versión.");
        setData(body);
      })
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "No se pudo cargar la pantalla."); });
    return () => controller.abort();
    // The projection belongs to the current URL; it loads once per mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return { data, error };
}

const SEVERITY: Record<string, "error" | "warning" | "info" | "success"> = { error: "error", warning: "warning", success: "success", info: "info", debug: "info" };

/** Django messages left by a native POST + redirect, shown once. */
export function Messages({ messages }: { messages: Message[] }) {
  if (!messages.length) return null;
  return <Stack spacing={1} sx={{ mb: 2 }}>
    {messages.map((message, index) => {
      const severity = SEVERITY[message.level] ?? "info";
      return <Alert key={index} severity={severity} role={severity === "error" || severity === "warning" ? "alert" : "status"}>{message.text}</Alert>;
    })}
  </Stack>;
}

export function Loading({ title, error }: { title: string; error: string }) {
  return <Box component="main" sx={{ p: { xs: 2, md: 3 } }}>
    <Typography variant="h5" component="h1" gutterBottom>{title}</Typography>
    {error ? <Alert severity="error" role="alert">{error}</Alert> : <p role="status">Cargando…</p>}
  </Box>;
}

function CsrfInput() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

function Header({ title, back, children }: { title: string; back: string; children?: ReactNode }) {
  return <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, mb: 2 }}>
    <Typography variant="h5" component="h1">{title}</Typography>
    <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
      <Button variant="outlined" color="inherit" size="small" href={internal(back)}>← Volver</Button>
      {children}
    </Stack>
  </Stack>;
}

type SortField = "id" | "periodo" | "estado" | "candidatos" | "validados" | "excluidos" | "creado";
const COLUMNS: [SortField, string][] = [
  ["id", "ID"], ["periodo", "Período"], ["estado", "Estado"], ["candidatos", "Candidatos"],
  ["validados", "Validados"], ["excluidos", "Excluidos"], ["creado", "Creado"],
];

export function PagosScreen() {
  const { data, error } = useProjection<PagosData>((body) => Array.isArray(body.rows) && !!body.provincia && !!body.urls);
  const [sort, setSort] = useState<{ field: SortField; ascending: boolean } | null>(null);
  const rows = useMemo(() => {
    if (!data || !sort) return data?.rows ?? [];
    return [...data.rows].sort((left, right) => {
      const a = left[sort.field], b = right[sort.field];
      const result = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "es", { numeric: true });
      return sort.ascending ? result : -result;
    });
  }, [data, sort]);
  if (!data) return <Loading title="Expedientes de pago" error={error} />;

  return <Box component="main" sx={{ p: { xs: 2, md: 3 } }}>
    <Header title={`Expedientes de pago — ${data.provincia.nombre}`} back={data.urls.volver}>
      <form action={internal(data.urls.crear)} method="post">
        <CsrfInput />
        <Button type="submit" variant="contained" color="success" size="small">Generar expediente de pago</Button>
      </form>
    </Header>
    <Messages messages={data.messages} />
    <TableContainer component={Paper}>
      <Table size="small" aria-label={`Expedientes de pago de ${data.provincia.nombre}`}>
        <TableHead>
          <TableRow>
            {COLUMNS.map(([field, label]) => <TableCell key={field} scope="col" aria-sort={sort?.field === field ? (sort.ascending ? "ascending" : "descending") : "none"}>
              <Button size="small" color="inherit" sx={{ fontWeight: 600, textTransform: "none", p: 0, minWidth: 0 }}
                onClick={() => setSort({ field, ascending: sort?.field === field ? !sort.ascending : true })}>{label}</Button>
            </TableCell>)}
            <TableCell scope="col"><span style={srOnly}>Acciones</span></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 && <TableRow><TableCell colSpan={8} align="center">No hay expedientes de pago.</TableCell></TableRow>}
          {rows.map((row) => <TableRow key={row.id} hover>
            <TableCell>{row.id}</TableCell>
            <TableCell>{row.periodo}</TableCell>
            <TableCell>{row.estado}</TableCell>
            <TableCell>{row.candidatos}</TableCell>
            <TableCell>{row.validados}</TableCell>
            <TableCell>{row.excluidos}</TableCell>
            <TableCell>{row.creado}</TableCell>
            <TableCell><Button variant="contained" size="small" href={internal(row.url)} aria-label={`Ver detalle del expediente ${row.id}`}>Ver</Button></TableCell>
          </TableRow>)}
        </TableBody>
      </Table>
    </TableContainer>
  </Box>;
}

export function PagoDetalleScreen() {
  const { data, error } = useProjection<PagoDetalleData>((body) => !!body.pago && !!body.urls && !!body.upload && Array.isArray(body.nomina));
  const [submitting, setSubmitting] = useState(false);
  if (!data) return <Loading title="Expediente de pago" error={error} />;
  const { pago, urls, upload } = data;
  const fields: [string, ReactNode][] = [
    ["Estado", pago.estado],
    ["Candidatos", pago.candidatos],
    ["Validados", pago.validados],
    ["Excluidos", pago.excluidos],
    ["Archivo de envío", <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1, alignItems: "center" }}>
      {urls.archivo_envio
        ? <Button variant="outlined" size="small" href={internal(urls.archivo_envio)}>Descargar Excel</Button>
        : <Typography component="span" color="text.secondary">No generado</Typography>}
      <Button variant="contained" color="success" size="small" href={internal(urls.exportar_nomina)}>Exportar nómina</Button>
    </Stack>],
  ];

  return <Box component="main" sx={{ p: { xs: 2, md: 3 } }}>
    <Header title={`Pago — ${pago.provincia.nombre} — ${pago.periodo}`} back={urls.volver} />
    <Messages messages={data.messages} />
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box component="dl" sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "minmax(10rem, 25%) 1fr" }, gap: 1, m: 0 }}>
        {fields.map(([label, value]) => [
          <Box component="dt" key={`${label}-dt`} sx={{ fontWeight: 600 }}>{label}</Box>,
          <Box component="dd" key={`${label}-dd`} sx={{ m: 0 }}>{value}</Box>,
        ])}
      </Box>
    </Paper>
    <Paper sx={{ p: 2 }} component="section" aria-labelledby="pago-subir-respuesta">
      <Typography variant="h6" component="h2" id="pago-subir-respuesta" gutterBottom>Subir respuesta de Sintys</Typography>
      {/* Regular multipart POST: the native view validates, processes and redirects back here. */}
      <form action={internal(upload.action)} method="post" encType="multipart/form-data" onSubmit={() => setSubmitting(true)}>
        <CsrfInput />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "flex-end" } }}>
          <Box sx={{ flex: 1, display: "flex", flexDirection: "column", gap: 0.5 }}>
            <label htmlFor="pago-archivo-respuesta">{upload.label}</label>
            <input id="pago-archivo-respuesta" type="file" name={upload.field} required={upload.required} />
          </Box>
          <Button type="submit" variant="contained" disabled={submitting}>Procesar respuesta</Button>
        </Stack>
      </form>
    </Paper>
    {data.nomina.length > 0 && <Paper sx={{ mt: 2 }} component="section">
      <Typography variant="h6" component="h2" id="pago-nomina-validada" sx={{ p: 2, pb: 1 }}>Nómina validada</Typography>
      <TableContainer>
        <Table size="small" aria-labelledby="pago-nomina-validada">
          <TableHead><TableRow>{["CUIL", "Nombre", "Apellido", "Estado", "Obs."].map((label) => <TableCell key={label} scope="col">{label}</TableCell>)}</TableRow></TableHead>
          <TableBody>
            {data.nomina.map((row, index) => <TableRow key={`${row.documento}-${index}`}>
              <TableCell>{row.documento}</TableCell>
              <TableCell>{row.nombre}</TableCell>
              <TableCell>{row.apellido}</TableCell>
              <TableCell>{row.estado}</TableCell>
              <TableCell>{row.observacion}</TableCell>
            </TableRow>)}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>}
  </Box>;
}
