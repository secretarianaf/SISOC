import Chip from "@mui/material/Chip";
import type { ChipProps } from "@mui/material/Chip";
import Box from "@mui/material/Box";

export type StateTone =
  | "success"
  | "error"
  | "warning"
  | "info"
  | "neutral"
  | "primary";

/**
 * State chip — MUI/Chip con la guía de color del DS.
 * Warning es lo que hay que mirar; error es lo que ya bloquea.
 * Es un chip de display: nunca lleva onClick dentro de una tarjeta clickeable.
 */
export default function StateChip({
  label,
  tone = "neutral",
  dot = false,
  size = "small",
  sx,
  ...rest
}: {
  label: string;
  tone?: StateTone;
  dot?: boolean;
} & Omit<ChipProps, "color" | "label">) {
  const isNeutral = tone === "neutral";

  return (
    <Chip
      size={size}
      label={label}
      color={isNeutral ? "default" : tone}
      variant={isNeutral ? "outlined" : "filled"}
      icon={
        dot ? (
          <Box
            component="span"
            sx={{
              width: 8,
              height: 8,
              borderRadius: (t) => `${t.radius.full}px`,
              bgcolor: "currentColor",
              ml: 1,
            }}
          />
        ) : undefined
      }
      sx={{ fontWeight: 500, ...sx }}
      {...rest}
    />
  );
}

/** Estado del expediente de celiaquía. */
export const toneExpediente = (estado: string): StateTone =>
  (
    ({
      CREADO: "neutral",
      EN_ESPERA: "info",
      CONFIRMACION_DE_ENVIO: "warning",
      RECEPCIONADO: "neutral",
      ASIGNADO: "primary",
      PROCESO_DE_CRUCE: "info",
      CRUCE_FINALIZADO: "success",
    }) as Record<string, StateTone>
  )[estado] ?? "neutral";

/** Revisión técnica de un legajo. */
export const toneRevision = (revision: string): StateTone =>
  (
    ({
      APROBADO: "success",
      RECHAZADO: "error",
      SUBSANAR: "warning",
      SUBSANADO: "info",
      PENDIENTE: "neutral",
    }) as Record<string, StateTone>
  )[revision] ?? "neutral";

/** Resultado del cruce Sintys. */
export const toneSintys = (resultado: string): StateTone =>
  resultado === "MATCH" ? "success" : resultado === "NO_MATCH" ? "error" : "neutral";

/** Estado de cupo del legajo. */
export const toneCupo = (estado: string): StateTone =>
  estado === "DENTRO" ? "primary" : estado === "FUERA" ? "warning" : "neutral";

/** Movimiento del histórico de cupo. */
export const toneMovimiento = (tipo: string): StateTone =>
  (
    ({
      ALTA: "success",
      BAJA: "error",
      SUSPENDIDO: "warning",
      REACTIVADO: "primary",
    }) as Record<string, StateTone>
  )[tipo] ?? "neutral";
