/**
 * Buscador PAS: la versión React de `pas/persona_list.html`. Consulta la misma
 * API (`/api/web/pas/personas/`) que el padrón del Panel de control.
 */
import { Alert, Box, Button, Card, CardContent, IconButton, InputAdornment, Link as MuiLink, MenuItem, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Tooltip, Typography } from "@mui/material";
import Add from "@mui/icons-material/Add";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ChevronLeft from "@mui/icons-material/ChevronLeft";
import ChevronRight from "@mui/icons-material/ChevronRight";
import Download from "@mui/icons-material/Download";
import Search from "@mui/icons-material/Search";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { exportarTokens, pasGet, type Padron } from "./api";
import { EstadoChip, Oculto, StateChip } from "./componentes";
import { Cargando, ErrorPas } from "./Estado";

export function BuscadorPage() {
  const [params, setParams] = useSearchParams();
  const query = useQuery({ queryKey: ["pas", "padron", params.toString()], queryFn: () => pasGet<Padron>(`personas/?${params}`) });
  const filtrado = Boolean(params.get("q") || params.get("estado"));
  function ir(page: number | null) {
    if (page === null) return;
    const next = new URLSearchParams(params);
    next.set("page", String(page));
    setParams(next);
  }
  const tokens = useMutation({ mutationFn: exportarTokens });
  const capabilities = query.data?.capabilities;
  return <Stack spacing={3}>
    <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}>
      <div>
        <Typography variant="overline" color="text.secondary" component="p">Programa de Acompañamiento Social</Typography>
        <Typography component="h1" variant="h5">Buscador PAS</Typography>
      </div>
      {capabilities && <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
        {capabilities.can_import && <>
          <Button component={Link} to="/buscador/nuevo" variant="outlined" startIcon={<Add />}>Nuevo titular</Button>
          <Button component={Link} to="/buscador/importar" variant="contained" startIcon={<ArrowUpwardIcon />}>Importar titulares</Button>
        </>}
        {capabilities.can_export_tokens && <Button variant="outlined" startIcon={<Download />}
          disabled={tokens.isPending} onClick={() => tokens.mutate()}>{tokens.isPending ? "Exportando…" : "Exportar tokens"}</Button>}
        <Button component={Link} to="/informes" variant="outlined">Informes</Button>
      </Stack>}
    </Stack>
    {tokens.isError && <Alert severity="error" onClose={() => tokens.reset()}>No se pudieron exportar los tokens. Reintentá en unos minutos.</Alert>}
    <Card>
      <CardContent sx={{ pb: 2 }}>
        <Stack component="form" role="search" noValidate direction={{ xs: "column", md: "row" }} spacing={2} key={params.toString()}
          onSubmit={(event) => {
            event.preventDefault();
            const fields = new FormData(event.currentTarget);
            const next = new URLSearchParams();
            const q = String(fields.get("q") ?? "").trim();
            const estado = String(fields.get("estado") ?? "");
            if (q) next.set("q", q);
            if (estado) next.set("estado", estado);
            setParams(next);
          }}>
          <TextField name="q" type="search" label="Buscar titular" placeholder="Nombre, CUIT, DNI o IdPersona" defaultValue={params.get("q") ?? ""}
            sx={{ flex: 1 }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><Search sx={{ color: "action.active" }} /></InputAdornment> } }} />
          <TextField select name="estado" label="Estado" defaultValue={params.get("estado") ?? ""} sx={{ width: { xs: "100%", md: 220 } }}>
            <MenuItem value="">Todos los estados</MenuItem>
            {(query.data?.estados ?? []).map(({ nombre }) => <MenuItem key={nombre} value={nombre}>{nombre}</MenuItem>)}
          </TextField>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Button type="submit" variant="contained" size="large" startIcon={<Search />}>Buscar</Button>
            {filtrado && <Button size="large" onClick={() => setParams(new URLSearchParams())}>Limpiar</Button>}
          </Stack>
        </Stack>
      </CardContent>
      {query.isPending ? <Box sx={{ p: 3 }}><Cargando /></Box> : query.isError ? <Box sx={{ p: 3 }}><ErrorPas error={query.error} /></Box> : <>
        <TableContainer sx={{ position: "relative" }}>
          <Table sx={{ minWidth: 820 }} aria-label="Titulares PAS">
            <TableHead><TableRow>
              <TableCell sx={{ pl: 3 }}>Titular</TableCell><TableCell>CUIT</TableCell><TableCell>Ubicación</TableCell>
              <TableCell>Estado</TableCell><TableCell>Avisos</TableCell>
              <TableCell align="right" sx={{ pr: 3 }}><Oculto>Acciones</Oculto></TableCell>
            </TableRow></TableHead>
            <TableBody>
              {!query.data.results.length && <TableRow><TableCell colSpan={6} sx={{ pl: 3, color: "text.secondary" }}>Sin titulares para los criterios seleccionados.</TableCell></TableRow>}
              {query.data.results.map((persona) => {
                const nombre = `${persona.apellidos}, ${persona.nombres}`;
                return <TableRow key={persona.id} hover>
                  <TableCell sx={{ pl: 3 }}>
                    <MuiLink component={Link} to={`/titulares/${persona.id}`} sx={{ typography: "subtitle2", display: "block" }}>{nombre}</MuiLink>
                    <Typography variant="caption" color="text.secondary">DNI {persona.dni}{persona.id_persona ? ` · IdPersona ${persona.id_persona}` : ""}</Typography>
                  </TableCell>
                  <TableCell>{persona.cuit || "—"}</TableCell>
                  <TableCell>
                    {persona.provincia || "—"}
                    {persona.municipio && <Typography variant="caption" color="text.secondary" component="span" sx={{ display: "block" }}>{persona.municipio}</Typography>}
                  </TableCell>
                  <TableCell><EstadoChip nombre={persona.estado.nombre} /></TableCell>
                  <TableCell>{persona.avisos?.length
                    ? <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap" }}>{persona.avisos.map((codigo) => <StateChip key={codigo} label={String(codigo)} />)}</Stack>
                    : <Typography variant="body2" color="text.secondary" component="span">Sin avisos</Typography>}</TableCell>
                  <TableCell align="right" sx={{ pr: 3 }}>
                    <Tooltip title="Abrir panel de control"><IconButton component={Link} to={`/titulares/${persona.id}`} size="small" color="primary"
                      aria-label={`Abrir panel de control de ${nombre}`}><ChevronRight /></IconButton></Tooltip>
                  </TableCell>
                </TableRow>;
              })}
            </TableBody>
          </Table>
        </TableContainer>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, px: 3, py: 1.5 }}>
          <Typography variant="body2" color="text.secondary">Padrón actual: {query.data.total_padron} {query.data.total_padron === 1 ? "titular" : "titulares"}</Typography>
          <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
            <Tooltip title="Página anterior"><span><IconButton aria-label="Página anterior" disabled={query.data.previous === null} onClick={() => ir(query.data.previous)}><ChevronLeft /></IconButton></span></Tooltip>
            {query.data.page_range?.length ? query.data.page_range.map((numero, i) => numero === "…"
              ? <Typography key={i} variant="body2" color="text.secondary" aria-hidden="true">…</Typography>
              : <Button key={i} size="small" variant={numero === query.data.page ? "contained" : "text"} sx={{ minWidth: 36 }}
                aria-label={`Página ${numero}`} aria-current={numero === query.data.page ? "page" : undefined} onClick={() => ir(numero)}>{numero}</Button>)
              : <Typography variant="body2">Página {query.data.page ?? 1}</Typography>}
            <Tooltip title="Página siguiente"><span><IconButton aria-label="Página siguiente" disabled={query.data.next === null} onClick={() => ir(query.data.next)}><ChevronRight /></IconButton></span></Tooltip>
          </Stack>
        </Stack>
      </>}
    </Card>
  </Stack>;
}
