import Chip from "@mui/material/Chip";
import Stack from "./Stack";

/**
 * Filter chip — MUI no tiene ChipGroup. El componente real es el grupo,
 * con la selección en el padre.
 */
export default function FilterChipGroup({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      {options.map((o) => {
        const selected = o.value === value;
        return (
          <Chip
            key={o.value}
            label={o.label}
            size="small"
            clickable
            color={selected ? "primary" : "default"}
            variant={selected ? "filled" : "outlined"}
            onClick={() => onChange(o.value)}
          />
        );
      })}
    </Stack>
  );
}
