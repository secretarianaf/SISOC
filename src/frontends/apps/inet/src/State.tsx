import { StateChip } from "@sisoc/ui";
import type { ComponentProps } from "react";

/** Variante compacta usada por las filas y encabezados de INET en Figma. */
export function InetStateChip(props: ComponentProps<typeof StateChip>) {
  return <StateChip {...props} variant="filled" sx={{ height: 20, fontSize: 12, "& .MuiChip-icon": { width: 6, height: 6 }, "& .MuiChip-label": { px: 1 } }} />;
}
