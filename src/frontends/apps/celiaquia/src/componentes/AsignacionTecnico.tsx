import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import { SectionCard, Stack, StateChip } from "@sisoc/ui";
import { mensajeDeError, SinPermiso } from "@sisoc/api";
import type { AsignacionTecnico } from "@sisoc/api";
import { api } from "../api";

/**
 * Asignación del técnico que va a revisar los legajos.
 *
 * Es el paso siguiente a recepcionar: hasta que no hay técnico asignado, nadie
 * puede revisar ni pedir subsanación.
 *
 * Solo coordinación y admin asignan. Si el usuario no puede, el endpoint de
 * técnicos devuelve 403 y la tarjeta se muestra en modo lectura: no se oculta,
 * porque saber quién está asignado le sirve igual a la provincia.
 */
export function AsignacionTecnico({
  expedienteId,
  asignaciones,
}: {
  expedienteId: number;
  asignaciones: AsignacionTecnico[];
}) {
  const queryClient = useQueryClient();
  const [tecnicoId, setTecnicoId] = useState("");
  const [error, setError] = useState("");

  const tecnicos = useQuery({
    queryKey: ["tecnicos"],
    queryFn: () => api.expedientes.tecnicos(),
    staleTime: Infinity,
    // Un 403 acá significa "no asignás", no un fallo: no se reintenta.
    retry: (fallos, e) => !(e instanceof SinPermiso) && fallos < 2,
  });

  const puedeAsignar = tecnicos.isSuccess;
  const activa = asignaciones.find((a) => a.activa);

  const refrescar = () =>
    queryClient.invalidateQueries({ queryKey: ["expediente", expedienteId] });

  const asignar = useMutation({
    mutationFn: () =>
      api.expedientes.asignarTecnico(expedienteId, Number(tecnicoId)),
    onSuccess: () => {
      setError("");
      setTecnicoId("");
      refrescar();
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const desasignar = useMutation({
    mutationFn: () => api.expedientes.desasignarTecnico(expedienteId),
    onSuccess: () => {
      setError("");
      refrescar();
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  const ocupado = asignar.isPending || desasignar.isPending;

  return (
    <SectionCard
      title={
        <Stack direction="row" spacing={1} alignItems="center">
          <span>Técnico asignado</span>
          {activa ? (
            <StateChip label={activa.tecnico.nombre} tone="success" />
          ) : (
            <StateChip label="Sin asignar" tone="warning" />
          )}
        </Stack>
      }
      subheader="Sin técnico asignado no se pueden revisar los legajos"
    >
      <Stack spacing={2}>
        {error ? (
          <Alert severity="error" onClose={() => setError("")}>
            {error}
          </Alert>
        ) : null}

        {puedeAsignar ? (
          <Stack direction="row" spacing={1} alignItems="flex-start" flexWrap="wrap" useFlexGap>
            <TextField
              select
              size="small"
              label="Técnico"
              value={tecnicoId}
              onChange={(e) => setTecnicoId(e.target.value)}
              sx={{ minWidth: 260 }}
              disabled={ocupado}
            >
              {(tecnicos.data ?? []).map((t) => (
                <MenuItem key={t.id} value={String(t.id)}>
                  {t.nombre}
                </MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained"
              startIcon={<PersonAddIcon />}
              disabled={!tecnicoId || ocupado}
              onClick={() => asignar.mutate()}
            >
              {asignar.isPending ? "Asignando…" : "Asignar"}
            </Button>
            {activa ? (
              <Button
                color="inherit"
                disabled={ocupado}
                onClick={() => desasignar.mutate()}
              >
                {desasignar.isPending ? "Quitando…" : "Quitar asignación"}
              </Button>
            ) : null}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {activa
              ? `Asignado a ${activa.tecnico.nombre}.`
              : "Todavía no hay un técnico asignado."}
          </Typography>
        )}

        {asignaciones.length > 1 ? (
          <Stack spacing={0.5}>
            <Typography variant="captionBold" color="text.secondary">
              Asignaciones anteriores
            </Typography>
            {asignaciones
              .filter((a) => !a.activa)
              .map((a) => (
                <Typography key={a.id} variant="caption" color="text.secondary">
                  {a.tecnico.nombre}
                </Typography>
              ))}
          </Stack>
        ) : null}
      </Stack>
    </SectionCard>
  );
}
