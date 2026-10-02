import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Stack from "./Stack";

export type StatTone =
  | "primary"
  | "secondary"
  | "success"
  | "warning"
  | "error";

/**
 * Stat card — no sigue la regla de severidad calculada.
 * El color refuerza el significado del dato: `primary` neutro/informativo,
 * `error` un problema, `warning` algo que pide atención, `success` resuelto,
 * `secondary` una cifra clave que se quiere destacar sin valorarla.
 */
export default function StatCard({
  label,
  value,
  tone = "primary",
  hint,
}: {
  label: string;
  value: React.ReactNode;
  tone?: StatTone;
  hint?: string;
}) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        <Stack spacing={0.5}>
          <Typography variant="captionBold" color="text.secondary">
            {label}
          </Typography>
          <Typography variant="h4Bold" sx={{ color: `${tone}.text` }}>
            {value}
          </Typography>
          {hint ? (
            <Typography variant="caption" color="text.secondary">
              {hint}
            </Typography>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}
