import { Box, Chip } from "@mui/material";

type Tone = "neutral" | "info" | "warning" | "success" | "error";

const stateTones: Record<string, Tone> = {
  borrador: "neutral",
  planificada: "neutral",
  presentado: "info",
  en_revision: "info",
  subsanado: "info",
  en_ejecucion: "info",
  en_progreso: "info",
  en_post_operativo: "info",
  observado: "warning",
  observada: "warning",
  en_subsanacion: "warning",
  checklist_pendiente: "warning",
  pendiente_habilitacion: "warning",
  pendiente_cierre: "warning",
  pendiente_cierre_observada: "warning",
  habilitada: "success",
  aprobado: "success",
  finalizada: "success",
  cerrada: "success",
  cerrada_final: "success",
  rechazado: "error",
  cancelado: "error",
};

export function StateChip({ state, label }: { state: string; label: string }) {
  const tone = stateTones[state] ?? "neutral";
  return <Chip
    component="span"
    data-state={state}
    data-tone={tone}
    size="small"
    variant="filled"
    label={label}
    icon={<Box component="span" aria-hidden="true" sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: 'currentColor' }} />}
    sx={(theme) => ({
      bgcolor: tone === "neutral" ? theme.palette.action.selected : theme.palette[tone].main,
      color: tone === "neutral" ? theme.palette.text.primary : theme.palette[tone].contrastText,
      borderRadius: theme.radius.full,
      height: 20,
      fontSize: 12,
      fontWeight: 400,
      letterSpacing: "0.4px",
      "& .MuiChip-label": { px: 1.5, lineHeight: "20px", fontSize: 12, letterSpacing: "0.4px" },
      "& .MuiChip-icon": { color: "inherit", ml: 1.5, mr: -0.75 },
    })}
  />;
}
