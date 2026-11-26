/**
 * Importar titulares: la versión React de `pas/titulares_import.html`, con la
 * misma API (`/api/web/pas/titulares/importar/`). Se abre dentro del módulo
 * desde el que se llega (Buscador PAS o Panel de control) para poder volver.
 */
import { useState, type FormEvent } from "react";
import { Alert, alpha, Box, Button, Card, Chip, Collapse, Link as MuiLink, Paper, Stack, Typography } from "@mui/material";
import ArrowBack from "@mui/icons-material/ArrowBack";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import InsertDriveFile from "@mui/icons-material/InsertDriveFileOutlined";
import UploadFile from "@mui/icons-material/UploadFile";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { pasGet, pasPost } from "./api";
import { Cargando, ErrorPas } from "./Estado";
import { ErrorOperacion } from "./Gestion";

type Resultado = { total: number; creados: number; duplicados: number; errores: string[] };

const OBLIGATORIAS = ["Apellidos", "Nombres", "DNI", "CUIT", "Provincia", "Municipio"];
const OPCIONALES = ["Género", "Calle", "Altura", "Email", "UltimoEstadoPas", "AvisoLiquidacion"];
const REGLAS = [
  "También se aceptan los encabezados Apellido y Nombre.",
  "Calle y Altura forman el domicilio; los opcionales vacíos quedan sin dato.",
  "Género admite M, F o X (encabezado Género, ciudadano_genero o ciudadano_genero_cod).",
  "Si no se informa UltimoEstadoPas, el titular queda Activo.",
  "Si el DNI o el CUIT ya existen, el registro se omite y el padrón no cambia.",
  "Cada titular nuevo recibe un IdPersona interno y un token DDJJ vigente.",
];

function tamanio(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Formato del CSV: columnas como chips y las reglas a demanda. */
function FormatoArchivo() {
  const [reglas, setReglas] = useState(false);
  return <Paper variant="outlined" component="aside" aria-labelledby="pas-import-formato" sx={(theme) => ({ p: 2.5, borderRadius: `${theme.radius.large}px` })}>
    <Typography id="pas-import-formato" component="h2" variant="subtitle1Medium">Formato del archivo</Typography>
    <Typography variant="overline" component="p" color="text.secondary" sx={{ pt: 1.5 }}>Columnas obligatorias</Typography>
    <Stack direction="row" useFlexGap spacing={0.75} sx={{ flexWrap: "wrap", pt: 0.5 }}>
      {OBLIGATORIAS.map((columna) => <Chip key={columna} size="small" color="primary" variant="outlined" label={columna} />)}
    </Stack>
    <Typography variant="overline" component="p" color="text.secondary" sx={{ pt: 1.5 }}>Opcionales</Typography>
    <Stack direction="row" useFlexGap spacing={0.75} sx={{ flexWrap: "wrap", pt: 0.5 }}>
      {OPCIONALES.map((columna) => <Chip key={columna} size="small" label={columna} />)}
    </Stack>
    <MuiLink component="button" type="button" variant="body2" aria-expanded={reglas} aria-controls="pas-import-reglas"
      onClick={() => setReglas(!reglas)} sx={{ mt: 2 }}>{reglas ? "Ocultar reglas de importación" : "Ver reglas de importación"}</MuiLink>
    <Collapse in={reglas} id="pas-import-reglas">
      <Box component="ul" sx={{ m: 0, mt: 1, pl: 2.5, typography: "body2", color: "text.secondary", "& li + li": { mt: 0.5 } }}>
        {REGLAS.map((regla) => <li key={regla}>{regla}</li>)}
      </Box>
    </Collapse>
  </Paper>;
}

function ResumenImportacion({ resultado }: { resultado: Resultado }) {
  const cifras: [string, number, "success" | "warning" | "error" | "info"][] = [
    ["Registros leídos", resultado.total, "info"], ["Titulares creados", resultado.creados, "success"],
    ["Omitidos por duplicado", resultado.duplicados, "warning"], ["Filas con error", resultado.errores.length, "error"],
  ];
  return <Stack spacing={1.5}>
    <Alert severity={resultado.errores.length ? "warning" : "success"}>Importación finalizada.</Alert>
    <Box component="dl" sx={{ m: 0, display: "grid", gap: 1, gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" } }}>
      {cifras.map(([label, valor, tono]) => <Box key={label} sx={(theme) => ({ p: 1.5, borderRadius: `${theme.radius.medium}px`,
        bgcolor: alpha(theme.palette[tono].main, 0.08) })}>
        <Typography component="dt" variant="caption" color="text.secondary">{label}</Typography>
        <Typography component="dd" variant="h6" sx={{ m: 0, color: `${tono}.text` }}>{valor}</Typography>
      </Box>)}
    </Box>
    {resultado.errores.length > 0 && <Alert severity="warning" variant="outlined">
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>{resultado.errores.map((item, index) => <li key={index}>{item}</li>)}</Box>
    </Alert>}
  </Stack>;
}

export function ImportarTitularesPage({ volver = "/", volverTexto = "Volver al Panel de control" }: { volver?: string; volverTexto?: string }) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const cache = useQueryClient();
  const consulta = useQuery({ queryKey: ["pas", "titulares/importar/"], queryFn: () => pasGet("titulares/importar/") });
  const importar = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("archivo", file);
      return pasPost<{ resultado: Resultado }>("titulares/importar/", form);
    },
    onSuccess: () => cache.invalidateQueries({ queryKey: ["pas", "padron"] }),
  });
  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) return <ErrorPas error={consulta.error} />;
  return <Stack spacing={3}>
    <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { md: "center" } }}>
      <div>
        <Typography variant="overline" color="text.secondary" component="p">Programa de Acompañamiento Social</Typography>
        <Typography component="h1" variant="h5">Importar titulares</Typography>
        <Typography variant="body2" color="text.secondary">Alta masiva de titulares desde un archivo CSV.</Typography>
      </div>
      <Button component={Link} to={volver} variant="outlined" startIcon={<ArrowBack />} sx={{ alignSelf: { xs: "flex-start", md: "center" } }}>{volverTexto}</Button>
    </Stack>
    <Box sx={{ display: "grid", gap: 3, alignItems: "start", gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "minmax(0, 1fr) 360px" } }}>
      <Card sx={{ p: 3 }}>
        <Stack component="form" spacing={2.5} onSubmit={(event: FormEvent<HTMLFormElement>) => {
          event.preventDefault();
          if (archivo && !importar.isPending) importar.mutate(archivo);
        }}>
          {/* Zona de carga: el input queda oculto detrás del botón de selección. */}
          <Box sx={(theme) => ({ p: 3, border: `${theme.border.focus}px dashed`, borderColor: archivo ? "primary.main" : "divider",
            borderRadius: `${theme.radius.large}px`, bgcolor: archivo ? alpha(theme.palette.primary.main, 0.04) : "transparent",
            display: "flex", flexDirection: { xs: "column", sm: "row" }, alignItems: { sm: "center" }, gap: 2 })}>
            {archivo ? <InsertDriveFile color="primary" sx={{ fontSize: 40 }} /> : <UploadFile sx={{ fontSize: 40, color: "text.secondary" }} />}
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="subtitle2" sx={{ overflowWrap: "anywhere" }}>{archivo ? archivo.name : "Seleccioná el archivo CSV del padrón"}</Typography>
              <Typography variant="caption" color="text.secondary" component="p">
                {archivo ? tamanio(archivo.size) : "Separado por coma, punto y coma o barra vertical, con encabezados en la primera fila."}
              </Typography>
            </Box>
            <Button component="label" variant="outlined" startIcon={<UploadFile />} disabled={importar.isPending} sx={{ flexShrink: 0 }}>
              {archivo ? "Cambiar archivo" : "Seleccionar archivo"}
              <input type="file" hidden accept=".csv,text/csv" aria-label="Archivo CSV" onChange={(event) => {
                setArchivo(event.target.files?.[0] ?? null);
                importar.reset();
                event.target.value = "";
              }} />
            </Button>
          </Box>
          {importar.isError && <ErrorOperacion error={importar.error} />}
          {importar.isSuccess && <ResumenImportacion resultado={importar.data.resultado} />}
          <Stack direction="row" spacing={1} sx={{ justifyContent: "flex-end" }}>
            <Button component={Link} to={volver}>Cancelar</Button>
            <Button type="submit" variant="contained" startIcon={<ArrowUpward />} disabled={!archivo || importar.isPending}>
              {importar.isPending ? "Importando…" : "Importar CSV"}
            </Button>
          </Stack>
        </Stack>
      </Card>
      <FormatoArchivo />
    </Box>
  </Stack>;
}
