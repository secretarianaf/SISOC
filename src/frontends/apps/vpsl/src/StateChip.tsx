import { Chip } from "@mui/material";
import CircleIcon from "@mui/icons-material/Circle";

export function StateChip({ state, label }: { state: string; label: string }) {
  return <Chip
    component="span"
    data-state={state}
    size="small"
    variant="outlined"
    label={label}
    icon={<CircleIcon />}
    sx={{
      bgcolor: "action.hover",
      color: "text.primary",
      borderColor: "input.outlinedBorder",
      "& .MuiChip-icon": { color: "inherit", fontSize: 9 },
    }}
  />;
}
