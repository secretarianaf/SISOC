import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import AttachFileIcon from "@mui/icons-material/AttachFile";
import { Stack } from "@sisoc/ui";
import { mensajeDeError } from "@sisoc/api";
import { api } from "../api";

export type MotivoElegido = {
  texto_libre: string;
  observaciones_ids: number[];
  documentacion_complementaria: File[];
};

/**
 * Motivo de una subsanación o un rechazo (issues #2592 y #2523).
 *
 * Cada instancia lleva solo las observaciones técnicas que se eligen acá, más
 * el texto libre: el back arma el motivo con eso y no con todo el historial.
 * Las que todavía no se le comunicaron a la provincia vienen tildadas, igual
 * que en la pantalla Django. Al subsanar se puede adjuntar documentación
 * complementaria para la provincia.
 *
 * El padre lo monta con una `key` por apertura, así cada vez arranca de cero.
 */
export function MotivoRevision({
  legajoId,
  accion,
  onCancelar,
  onConfirmar,
}: {
  legajoId: number;
  accion: "SUBSANAR" | "RECHAZAR" | null;
  onCancelar: () => void;
  onConfirmar: (motivo: MotivoElegido) => void;
}) {
  const abierto = accion !== null;
  const [textoLibre, setTextoLibre] = useState("");
  // `null` hasta que se toca algo: mientras tanto valen las pendientes.
  const [tocadas, setTocadas] = useState<number[] | null>(null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const input = useRef<HTMLInputElement | null>(null);

  const opciones = useQuery({
    queryKey: ["legajo", legajoId, "motivo-preview"],
    queryFn: () => api.legajos.motivoPreview(legajoId),
    enabled: abierto,
  });

  const elegidas =
    tocadas ??
    (opciones.data?.opciones ?? []).filter((o) => o.pendiente).map((o) => o.id);

  const alternar = (id: number) =>
    setTocadas(
      elegidas.includes(id)
        ? elegidas.filter((x) => x !== id)
        : [...elegidas, id],
    );

  // Sin observaciones ni texto no hay nada que comunicar: el back lo rechaza.
  const vacio = elegidas.length === 0 && !textoLibre.trim();

  return (
    <Dialog open={abierto} onClose={onCancelar} maxWidth="sm" fullWidth>
      <DialogTitle>
        {accion === "RECHAZAR" ? "Motivo del rechazo" : "Motivo de la subsanación"}
      </DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          {opciones.isError ? (
            <Alert severity="error">{mensajeDeError(opciones.error)}</Alert>
          ) : null}
          {opciones.data && opciones.data.opciones.length > 0 ? (
            <Stack spacing={0.5}>
              <Typography variant="captionBold" color="text.secondary">
                Observaciones técnicas a comunicar
              </Typography>
              {opciones.data.opciones.map((o) => (
                <FormControlLabel
                  key={o.id}
                  control={
                    <Checkbox
                      checked={elegidas.includes(o.id)}
                      onChange={() => alternar(o.id)}
                    />
                  }
                  label={o.etiqueta}
                />
              ))}
            </Stack>
          ) : null}
          {opciones.data && opciones.data.opciones.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              El legajo no tiene observaciones técnicas: el motivo es el texto
              complementario.
            </Typography>
          ) : null}
          <TextField
            label="Texto complementario"
            multiline
            minRows={3}
            fullWidth
            value={textoLibre}
            onChange={(e) => setTextoLibre(e.target.value)}
          />
          {accion === "SUBSANAR" ? (
            <Stack spacing={1}>
              <input
                ref={input}
                type="file"
                multiple
                hidden
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={(e) => {
                  setArchivos(Array.from(e.target.files ?? []));
                  e.target.value = "";
                }}
              />
              <Button
                variant="outlined"
                startIcon={<AttachFileIcon />}
                onClick={() => input.current?.click()}
              >
                Adjuntar documentación complementaria
              </Button>
              {archivos.map((a) => (
                <Typography key={a.name} variant="body2" color="text.secondary">
                  {a.name}
                </Typography>
              ))}
            </Stack>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancelar}>Cancelar</Button>
        <Button
          variant="contained"
          color={accion === "RECHAZAR" ? "error" : "warning"}
          disabled={vacio || opciones.isLoading}
          onClick={() =>
            onConfirmar({
              texto_libre: textoLibre,
              observaciones_ids: elegidas,
              documentacion_complementaria: archivos,
            })
          }
        >
          Confirmar
        </Button>
      </DialogActions>
    </Dialog>
  );
}
