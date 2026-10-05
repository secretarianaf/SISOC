import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import CheckIcon from "@mui/icons-material/CheckCircle";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { Stack } from "@sisoc/ui";
import { mensajeDeError } from "@sisoc/api";
import type { ArchivoLegajo } from "@sisoc/api";
import { api } from "../api";

/** Formatos que acepta la pantalla Django; se replica para no frustrar la subida. */
const FORMATOS = ".pdf,.jpg,.jpeg,.png";

/**
 * Documentación de un legajo.
 *
 * Se habilita una vez procesado el Excel: recién ahí existen los legajos. Qué
 * archivos pide cada uno depende del rol (beneficiario, responsable o ambos) y
 * lo decide el back en `legajo.archivos`; acá no se asume nada.
 *
 * El expediente no se puede enviar hasta que todos los legajos tengan sus
 * archivos, así que el estado de cada slot se muestra explícito.
 */
export function ArchivosLegajo({
  legajoId,
  expedienteId,
  archivos,
  deshabilitado = false,
}: {
  legajoId: number;
  expedienteId: number;
  archivos: ArchivoLegajo[];
  deshabilitado?: boolean;
}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const [slotEnCurso, setSlotEnCurso] = useState<number | null>(null);
  const inputs = useRef<Record<number, HTMLInputElement | null>>({});

  const subir = useMutation({
    mutationFn: ({ archivo, slot }: { archivo: File; slot: number }) =>
      api.legajos.subirArchivo(legajoId, archivo, slot),
    onSuccess: () => {
      setError("");
      // El legajo cambia `archivos_ok`, que es lo que habilita el envío.
      queryClient.invalidateQueries({
        queryKey: ["expediente", expedienteId, "legajos"],
      });
    },
    onError: (e) => setError(mensajeDeError(e)),
    onSettled: () => setSlotEnCurso(null),
  });

  if (archivos.length === 0) return null;

  const faltantes = archivos.filter((a) => !a.cargado).length;

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Typography variant="captionBold" color="text.secondary">
          Documentación
        </Typography>
        {faltantes === 0 ? (
          <Chip
            size="small"
            icon={<CheckIcon />}
            color="success"
            variant="outlined"
            label="Completa"
          />
        ) : (
          <Chip
            size="small"
            color="warning"
            variant="outlined"
            label={`Faltan ${faltantes}`}
          />
        )}
      </Stack>

      {error ? (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      ) : null}

      {archivos.map((a) => (
        <Stack
          key={a.campo}
          direction="row"
          spacing={1}
          alignItems="center"
          flexWrap="wrap"
          useFlexGap
        >
          <input
            ref={(el) => {
              inputs.current[a.slot] = el;
            }}
            type="file"
            accept={FORMATOS}
            hidden
            onChange={(e) => {
              const archivo = e.target.files?.[0];
              if (archivo) {
                setSlotEnCurso(a.slot);
                subir.mutate({ archivo, slot: a.slot });
              }
              e.target.value = "";
            }}
          />
          <Button
            size="small"
            variant={a.cargado ? "text" : "outlined"}
            startIcon={<UploadFileIcon />}
            disabled={deshabilitado || subir.isPending}
            onClick={() => inputs.current[a.slot]?.click()}
          >
            {slotEnCurso === a.slot && subir.isPending
              ? "Subiendo…"
              : a.cargado
                ? "Reemplazar"
                : "Subir"}
          </Button>
          <Typography variant="body2" sx={{ flex: 1, minWidth: 180 }}>
            {a.etiqueta}
          </Typography>
          {a.cargado && a.url ? (
            <Link href={a.url} target="_blank" rel="noopener" variant="body2">
              Ver archivo
            </Link>
          ) : (
            <Typography variant="caption" sx={{ color: "warning.text" }}>
              Sin cargar
            </Typography>
          )}
        </Stack>
      ))}
    </Stack>
  );
}
