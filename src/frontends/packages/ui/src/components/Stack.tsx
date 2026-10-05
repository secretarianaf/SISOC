import MuiStack from "@mui/material/Stack";
import type { StackProps as MuiStackProps } from "@mui/material/Stack";
import type { SxProps, Theme } from "@mui/material/styles";
import type { CSSProperties } from "react";

type Responsive<T> = T | Partial<Record<"xs" | "sm" | "md" | "lg" | "xl", T>>;

export type StackProps = MuiStackProps & {
  justifyContent?: Responsive<CSSProperties["justifyContent"]>;
  alignItems?: Responsive<CSSProperties["alignItems"]>;
  flexWrap?: Responsive<CSSProperties["flexWrap"]>;
};

/**
 * Stack con los props de alineación de siempre.
 * En esta versión de MUI el Stack ya no acepta system props sueltos: los
 * traducimos a `sx` acá para no repetir el objeto en cada pantalla.
 */
export default function Stack({
  justifyContent,
  alignItems,
  flexWrap,
  sx,
  ...rest
}: StackProps) {
  const layout = { justifyContent, alignItems, flexWrap } as SxProps<Theme>;

  return (
    <MuiStack
      sx={[layout, ...(Array.isArray(sx) ? sx : [sx])] as SxProps<Theme>}
      {...rest}
    />
  );
}
