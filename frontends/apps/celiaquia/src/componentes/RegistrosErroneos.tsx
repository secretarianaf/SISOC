import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Autocomplete from "@mui/material/Autocomplete";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import ReplayIcon from "@mui/icons-material/Replay";
import { SectionCard, Stack, StateChip } from "@sisoc/ui";
import { camposInvalidosDeError, mensajeDeError } from "@sisoc/api";
import type { RegistroErroneo } from "@sisoc/api";
import { api } from "../api";

type Fila = Record<string, string>;

/** `datos_raw` es la fila cruda del Excel: sus claves son las columnas. */
const filaDe = (registro: RegistroErroneo): Fila => {
  const crudo = (registro.datos_raw ?? {}) as Record<string, unknown>;
  return Object.fromEntries(
    Object.entries(crudo).map(([k, v]) => [k, v == null ? "" : String(v)]),
  );
};

const etiqueta = (campo: string) =>
  campo.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

/**
 * Editor de una fila con error.
 *
 * Se editan las columnas que trae `datos_raw`, no una lista fija: asi la
 * pantalla sirve para cualquier Excel y no hay que mantener del lado del front
 * la lista de campos que acepta el back.
 */
/**
 * Campos que el back guarda como **id**, no como texto.
 *
 * El Excel trae "F", "ARGENTINA" o codigos de otro sistema, y por eso falla la
 * importacion con "municipio 40 no encontrado". Con un input de texto no hay
 * forma de corregirlo: nadie conoce el id interno. Van como desplegable, igual
 * que en la pantalla Django.
 */
const CAMPOS_CATALOGO = [
  "sexo",
  "nacionalidad",
  "municipio",
  "localidad",
  "sexo_responsable",
];

/**
 * La localidad del responsable no tiene municipio propio: el validador lo
 * deriva de la localidad elegida. Asi que hay que ofrecer toda la provincia,
 * que llega a 2.699 opciones. Con buscador, no con un desplegable largo.
 */
const CAMPO_LOCALIDAD_RESPONSABLE = "localidad_responsable";

function ModalEdicion({
  registro,
  expedienteId,
  onCerrar,
}: {
  registro: RegistroErroneo;
  expedienteId: number;
  onCerrar: () => void;
}) {
  const queryClient = useQueryClient();
  const [valores, setValores] = useState<Fila>(() => filaDe(registro));
  const [invalidos, setInvalidos] = useState<string[]>([]);
  const [error, setError] = useState("");

  const catalogos = useQuery({
    queryKey: ["catalogos"],
    queryFn: () => api.expedientes.catalogos(),
    staleTime: Infinity,
  });
  const municipios = useQuery({
    queryKey: ["municipios", expedienteId],
    queryFn: () => api.expedientes.municipios(expedienteId),
    staleTime: Infinity,
  });
  // Las localidades son 15.394: se piden solo las del municipio elegido, y solo
  // si ese municipio existe de verdad. El Excel suele traer un codigo de otro
  // sistema ("40"), y pedir localidades de un municipio inexistente no sirve.
  const municipioId = Number(valores.municipio);
  const municipioValido = (municipios.data ?? []).some(
    (m) => m.id === municipioId,
  );
  const localidades = useQuery({
    queryKey: ["localidades", municipioId],
    queryFn: () =>
      api.expedientes.localidades(expedienteId, { municipio: municipioId }),
    enabled: municipioValido,
    staleTime: Infinity,
  });

  const localidadesProvincia = useQuery({
    queryKey: ["localidades-provincia", expedienteId],
    queryFn: () => api.expedientes.localidades(expedienteId),
    enabled: CAMPO_LOCALIDAD_RESPONSABLE in valores,
    staleTime: Infinity,
  });

  const opciones = useMemo(
    () => ({
      sexo: catalogos.data?.sexos ?? [],
      nacionalidad: catalogos.data?.nacionalidades ?? [],
      municipio: municipios.data ?? [],
      sexo_responsable: catalogos.data?.sexos ?? [],
      localidad: (localidades.data ?? []).map((l) => ({
        id: l.localidad_id,
        nombre: l.localidad_nombre,
      })),
    }),
    [catalogos.data, municipios.data, localidades.data],
  );

  const guardar = useMutation({
    mutationFn: () =>
      api.expedientes.actualizarRegistroErroneo(
        expedienteId,
        registro.id,
        valores,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["expediente", expedienteId, "registros-erroneos"],
      });
      onCerrar();
    },
    onError: (e) => {
      // El back devuelve el detalle y los campos que hay que resaltar.
      setError(mensajeDeError(e));
      setInvalidos(camposInvalidosDeError(e));
    },
  });

  const cambiar = (campo: string, valor: string) =>
    setValores((previo) => ({
      ...previo,
      [campo]: valor,
      // Cambiar de municipio invalida la localidad elegida.
      ...(campo === "municipio" ? { localidad: "" } : {}),
    }));

  const campos = Object.keys(valores);

  return (
    <Dialog open onClose={onCerrar} maxWidth="md" fullWidth>
      <DialogTitle>Corregir fila {registro.fila_excel}</DialogTitle>
      <DialogContent dividers>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <Grid container spacing={2}>
          {campos.map((campo) => {
            const esCatalogo = CAMPOS_CATALOGO.includes(campo);
            const lista = esCatalogo
              ? opciones[campo as keyof typeof opciones]
              : [];
            // El valor del Excel puede no estar en el catalogo (un codigo de
            // otro sistema). Se muestra vacio para obligar a elegir uno valido,
            // que es justo lo que destraba la importacion.
            const valorActual = valores[campo] ?? "";
            const enLista = lista.some((o) => String(o.id) === valorActual);

            if (campo === CAMPO_LOCALIDAD_RESPONSABLE) {
              const lista = localidadesProvincia.data ?? [];
              const elegida =
                lista.find((l) => String(l.localidad_id) === valorActual) ?? null;
              return (
                <Grid key={campo} size={{ xs: 12, sm: 6 }}>
                  <Autocomplete
                    options={lista}
                    value={elegida}
                    // El municipio se repite entre provincias y los nombres de
                    // localidad tambien: se muestra el municipio para desambiguar.
                    getOptionLabel={(o) =>
                      `${o.localidad_nombre} (${o.municipio_nombre})`
                    }
                    isOptionEqualToValue={(o, v) =>
                      o.localidad_id === v.localidad_id
                    }
                    onChange={(_, o) =>
                      cambiar(campo, o ? String(o.localidad_id) : "")
                    }
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        size="small"
                        label={etiqueta(campo)}
                        error={invalidos.includes(campo)}
                        helperText={
                          valorActual && !elegida
                            ? `El archivo traía "${valorActual}": elegí la localidad`
                            : undefined
                        }
                      />
                    )}
                  />
                </Grid>
              );
            }

            return (
              <Grid key={campo} size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  size="small"
                  select={esCatalogo}
                  label={etiqueta(campo)}
                  value={esCatalogo && !enLista ? "" : valorActual}
                  error={invalidos.includes(campo)}
                  disabled={campo === "localidad" && !municipioValido}
                  helperText={
                    campo === "localidad" && !municipioValido
                      ? "Elegí primero un municipio válido"
                      : esCatalogo && valorActual && !enLista
                        ? `El archivo traía "${valorActual}": elegí el valor correcto`
                        : undefined
                  }
                  onChange={(e) => cambiar(campo, e.target.value)}
                >
                  {esCatalogo
                    ? lista.map((o) => (
                        <MenuItem key={o.id} value={String(o.id)}>
                          {o.nombre}
                        </MenuItem>
                      ))
                    : null}
                </TextField>
              </Grid>
            );
          })}
        </Grid>
        {campos.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            La fila no tiene datos para editar.
          </Typography>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={onCerrar}>Cancelar</Button>
        <Button
          variant="contained"
          onClick={() => guardar.mutate()}
          disabled={guardar.isPending || campos.length === 0}
        >
          {guardar.isPending ? "Guardando…" : "Guardar"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/**
 * Filas del Excel que no se pudieron importar.
 *
 * Corregir, reprocesar y descartar pasan por `/api/celiaquia/`, que delega en
 * `registros_erroneos_service`: el mismo que usa la pantalla Django, asi que la
 * validacion es identica en los dos frentes.
 */
export function RegistrosErroneos({
  registros,
  expedienteId,
  soloLectura = false,
}: {
  registros: RegistroErroneo[];
  expedienteId: number;
  soloLectura?: boolean;
}) {
  const queryClient = useQueryClient();
  const [editando, setEditando] = useState<RegistroErroneo | null>(null);
  const [aviso, setAviso] = useState("");
  const [error, setError] = useState("");

  const refrescar = () => {
    queryClient.invalidateQueries({
      queryKey: ["expediente", expedienteId, "registros-erroneos"],
    });
    // Reprocesar crea legajos: la lista de al lado tambien queda vieja.
    queryClient.invalidateQueries({
      queryKey: ["expediente", expedienteId, "legajos"],
    });
  };

  const reprocesar = useMutation({
    mutationFn: () => api.expedientes.reprocesarRegistrosErroneos(expedienteId),
    onSuccess: (resumen) => {
      setError("");
      setAviso(
        `Se crearon ${resumen.creados} legajos. ` +
          `Quedan ${resumen.registros_restantes} filas con error` +
          (resumen.excluidos
            ? `, ${resumen.excluidos} excluidas por estar en otro expediente.`
            : "."),
      );
      refrescar();
    },
    onError: (e) => {
      setAviso("");
      setError(mensajeDeError(e));
    },
  });

  const eliminar = useMutation({
    mutationFn: (registroId: number) =>
      api.expedientes.eliminarRegistroErroneo(expedienteId, registroId),
    onSuccess: () => {
      setError("");
      setAviso("Fila descartada.");
      refrescar();
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const ocupado = reprocesar.isPending || eliminar.isPending;

  if (registros.length === 0 && !aviso && !error) return null;

  return (
    <SectionCard
      title={
        <Stack direction="row" spacing={1} alignItems="center">
          <span>Registros con error</span>
          <StateChip label={`${registros.length}`} tone="error" />
        </Stack>
      }
      subheader={
        soloLectura
          ? "Solo lectura: no tenés permisos para corregirlos"
          : "Corregí la fila y reprocesá para crear los legajos"
      }
      action={
        soloLectura ? undefined : (
          <Button
            startIcon={<ReplayIcon />}
            onClick={() => reprocesar.mutate()}
            disabled={ocupado || registros.length === 0}
          >
            {reprocesar.isPending ? "Reprocesando…" : "Reprocesar todas"}
          </Button>
        )
      }
      disableGutters
    >
      <Collapse in={Boolean(aviso)} unmountOnExit>
        <Alert
          severity="success"
          sx={{ mx: 2, mb: 1 }}
          onClose={() => setAviso("")}
        >
          {aviso}
        </Alert>
      </Collapse>
      <Collapse in={Boolean(error)} unmountOnExit>
        <Alert
          severity="error"
          sx={{ mx: 2, mb: 1 }}
          onClose={() => setError("")}
        >
          {error}
        </Alert>
      </Collapse>

      {reprocesar.data?.errores_detalle?.length ? (
        <Alert severity="warning" sx={{ mx: 2, mb: 1 }}>
          <Typography variant="captionBold" component="div">
            Filas que siguieron fallando
          </Typography>
          {reprocesar.data.errores_detalle.slice(0, 5).map((detalle) => (
            <Typography key={detalle} variant="caption" component="div">
              {detalle}
            </Typography>
          ))}
        </Alert>
      ) : null}

      <TableContainer sx={{ overflowX: "auto" }}>
        <Table size="small" sx={{ minWidth: 798 }}>
          <TableHead>
            <TableRow>
              <TableCell width="8%">Fila</TableCell>
              <TableCell width="34%">Datos</TableCell>
              <TableCell width="42%">Error</TableCell>
              {soloLectura ? null : (
                <TableCell width="16%" align="right">
                  Acciones
                </TableCell>
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {registros.map((r) => {
              const fila = filaDe(r);
              return (
                <TableRow key={r.id} hover>
                  <TableCell>
                    <StateChip label={`${r.fila_excel}`} tone="neutral" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {fila.apellido || "—"}, {fila.nombre || "—"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {fila.documento || "sin documento"}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ color: "error.text" }}>
                      {r.mensaje_error}
                    </Typography>
                    {r.campo_error ? (
                      <Typography variant="caption" color="text.secondary">
                        Campo: {r.campo_error}
                      </Typography>
                    ) : null}
                  </TableCell>
                  {soloLectura ? null : (
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        aria-label={`Corregir la fila ${r.fila_excel}`}
                        onClick={() => setEditando(r)}
                        disabled={ocupado}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Descartar la fila ${r.fila_excel}`}
                        onClick={() => eliminar.mutate(r.id)}
                        disabled={ocupado}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
            {registros.length === 0 ? (
              <TableRow>
                <TableCell colSpan={soloLectura ? 3 : 4}>
                  <Typography variant="body2" color="text.secondary">
                    No quedan filas con error.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </TableContainer>

      {editando ? (
        <ModalEdicion
          registro={editando}
          expedienteId={expedienteId}
          onCerrar={() => setEditando(null)}
        />
      ) : null}
    </SectionCard>
  );
}
