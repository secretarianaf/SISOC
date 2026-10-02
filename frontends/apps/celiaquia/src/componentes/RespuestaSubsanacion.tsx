import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import { Stack } from "@sisoc/ui";
import { mensajeDeError } from "@sisoc/api";
import { api } from "../api";

/** Los mismos formatos que acepta la pantalla Django. */
const FORMATOS = ".pdf,.jpg,.jpeg,.png";

/**
 * Respuesta de la provincia a una subsanación.
 *
 * Solo aparece cuando el legajo está en SUBSANAR: el back lo exige
 * (`SubsanacionService.exigir_puede_responder`) y mostrar el formulario
 * cuando no corresponde solo lleva a un 400.
 *
 * Los archivos son **evidencia nueva**: no reemplazan la documentación
 * original del legajo, se suman. Por eso se adjuntan varios de una vez.
 */
export function RespuestaSubsanacion({
  legajoId,
  expedienteId,
  motivo,
  deshabilitado = false,
}: {
  legajoId: number;
  expedienteId: number;
  motivo?: string | null;
  deshabilitado?: boolean;
}) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement | null>(null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const [descripcion, setDescripcion] = useState("");
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  const responder = useMutation({
    mutationFn: () =>
      api.legajos.responderSubsanacion(legajoId, archivos, {
        descripcion: descripcion.trim() || undefined,
      }),
    onSuccess: (r) => {
      setError("");
      setAviso(r.detail ?? "Archivos cargados.");
      setArchivos([]);
      setDescripcion("");
      queryClient.invalidateQueries({
        queryKey: ["expediente", expedienteId, "legajos"],
      });
    },
    onError: (e) => setError(mensajeDeError(e)),
  });

  return (
    <Stack spacing={1.5}>
      <Stack spacing={0.5}>
        <Typography variant="captionBold" color="text.secondary">
          Subsanación solicitada
        </Typography>
        <Typography variant="body2">
          {motivo || "Sin motivo registrado."}
        </Typography>
      </Stack>

      {error ? (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      ) : null}
      {aviso ? (
        <Alert severity="success" onClose={() => setAviso("")}>
          {aviso}
        </Alert>
      ) : null}

      <input
        ref={input}
        type="file"
        accept={FORMATOS}
        multiple
        hidden
        onChange={(e) => {
          setArchivos(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />

      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AttachFileIcon />}
          disabled={deshabilitado || responder.isPending}
          onClick={() => input.current?.click()}
        >
          Adjuntar evidencia
        </Button>
        {archivos.map((a) => (
          <Chip
            key={a.name}
            size="small"
            label={a.name}
            onDelete={() =>
              setArchivos((previos) => previos.filter((x) => x !== a))
            }
          />
        ))}
      </Stack>

      <TextField
        size="small"
        multiline
        minRows={2}
        label="Descripción (opcional)"
        value={descripcion}
        onChange={(e) => setDescripcion(e.target.value)}
        disabled={deshabilitado || responder.isPending}
      />

      <Stack direction="row" spacing={1} alignItems="center">
        <Button
          variant="contained"
          size="small"
          disabled={
            deshabilitado || responder.isPending || archivos.length === 0
          }
          onClick={() => responder.mutate()}
        >
          {responder.isPending ? "Enviando…" : "Enviar respuesta"}
        </Button>
        {archivos.length === 0 ? (
          <Typography variant="caption" color="text.secondary">
            Adjuntá al menos un archivo
          </Typography>
        ) : null}
      </Stack>
    </Stack>
  );
}
