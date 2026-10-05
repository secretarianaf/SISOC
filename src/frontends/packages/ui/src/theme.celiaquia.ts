/**
 * Tema de Celiaquia.
 *
 * **Deuda conocida:** `theme.ts` (VPSL) y este archivo son dos
 * implementaciones de la misma skill de diseno, hechas en paralelo. Se dejan
 * separadas a proposito: unificarlas es una decision de diseno que cambia como
 * se ve alguna de las dos apps, y no se puede verificar sin mirarlas. Conviene
 * resolverlo en un PR dedicado, no dentro de un merge.
 */

import { createTheme, alpha } from "@mui/material/styles";
import type { Theme } from "@mui/material/styles";
import type { PaletteMode } from "@mui/material";

/**
 * Theme del SISOC Design System.
 *
 * Los tokens del grupo `nav`, `info.main`, los radios, bordes, tamaños de ícono
 * y las seis variantes tipográficas propias vienen documentados en
 * `especificacion-theme.md`. El resto de las familias de color se arma sobre los
 * valores nativos de MUI siguiendo las reglas de esa misma especificación
 * (`.text` por severidad, `.darker` en warning y secondary).
 */

declare module "@mui/material/styles" {
  interface Theme {
    radius: {
      small: number;
      base: number;
      medium: number;
      large: number;
      full: number;
    };
    border: { thin: number; focus: number; accent: number };
    iconSize: {
      small: number;
      medium: number;
      large: number;
      buttonSmall: number;
      buttonLarge: number;
    };
  }
  interface ThemeOptions {
    radius?: Theme["radius"];
    border?: Theme["border"];
    iconSize?: Theme["iconSize"];
  }

  interface PaletteColor {
    text?: string;
    darker?: string;
  }
  interface SimplePaletteColorOptions {
    text?: string;
    darker?: string;
  }

  interface NavPalette {
    surface: string;
    surfaceSelected: string;
    text: string;
    textMuted: string;
    accent: string;
    hover: string;
    selected: string;
    divider: string;
  }

  interface Palette {
    nav: NavPalette;
    input: { outlinedBorder: string };
  }
  interface PaletteOptions {
    nav?: NavPalette;
    input?: { outlinedBorder: string };
  }

  interface TypographyVariants {
    h4Bold: React.CSSProperties;
    subtitle1Medium: React.CSSProperties;
    buttonSmall: React.CSSProperties;
    buttonLarge: React.CSSProperties;
    chip: React.CSSProperties;
    captionBold: React.CSSProperties;
  }
  interface TypographyVariantsOptions {
    h4Bold?: React.CSSProperties;
    subtitle1Medium?: React.CSSProperties;
    buttonSmall?: React.CSSProperties;
    buttonLarge?: React.CSSProperties;
    chip?: React.CSSProperties;
    captionBold?: React.CSSProperties;
  }
}

declare module "@mui/material/Typography" {
  interface TypographyPropsVariantOverrides {
    h4Bold: true;
    subtitle1Medium: true;
    buttonSmall: true;
    buttonLarge: true;
    chip: true;
    captionBold: true;
  }
}

const radius = { small: 2, base: 4, medium: 8, large: 16, full: 9999 };
const border = { thin: 1, focus: 2, accent: 4 };
const iconSize = {
  small: 20,
  medium: 24,
  large: 35,
  buttonSmall: 14,
  buttonLarge: 18,
};

/** Regla de severidad unificada: Score chip, Circular y Linear progress. */
export const severidad = (
  pts: number,
  requerido = 100,
): "error" | "warning" | "success" =>
  pts === 0 ? "error" : pts < requerido ? "warning" : "success";

const nav = (mode: PaletteMode) => ({
  surface: mode === "light" ? "#045F5B" : "#073B38",
  surfaceSelected: mode === "light" ? "#033F3C" : "#0A5D58",
  text: "#FAFAF9",
  textMuted: "#D6D3D1",
  accent: "#FFC107",
  hover: "rgba(255, 255, 255, 0.08)",
  selected: "rgba(255, 255, 255, 0.16)",
  divider: "rgba(255, 255, 255, 0.12)",
});

const palette = (mode: PaletteMode) => {
  const light = mode === "light";
  return {
    mode,
    primary: {
      light: "#3D8C88",
      main: "#045F5B",
      dark: "#033F3C",
      contrastText: "#FFFFFF",
      text: light ? "#033F3C" : "#6FB3AF",
    },
    secondary: {
      light: "#FFD54F",
      main: "#FFC107",
      dark: "#FFA000",
      darker: "#8C5A00",
      contrastText: "rgba(0, 0, 0, 0.87)",
      text: light ? "#8C5A00" : "#FFD54F",
    },
    error: {
      light: "#EF5350",
      main: "#D32F2F",
      dark: "#C62828",
      contrastText: "#FFFFFF",
      text: light ? "#C62828" : "#F28B82",
    },
    warning: {
      light: "#FF9800",
      main: "#ED6C02",
      dark: "#E65100",
      darker: "#8A3D00",
      contrastText: "#FFFFFF",
      text: light ? "#8A3D00" : "#FFB74D",
    },
    info: {
      light: "#03A9F4",
      main: "#01699F",
      dark: "#01579B",
      contrastText: "#FFFFFF",
      text: light ? "#01579B" : "#7FD1F5",
    },
    success: {
      light: "#4CAF50",
      main: "#2E7D32",
      dark: "#1B5E20",
      contrastText: "#FFFFFF",
      text: light ? "#1B5E20" : "#81C784",
    },
    grey: {
      50: "#FAFAF9",
      100: "#F5F5F4",
      200: "#E7E5E4",
      300: "#D6D3D1",
      400: "#A8A29E",
      500: "#78716C",
      600: "#57534E",
      700: "#44403C",
      800: "#292524",
      900: "#1C1917",
    },
    background: {
      default: light ? "#F5F5F4" : "#1C1917",
      paper: light ? "#FFFFFF" : "#292524",
    },
    text: {
      primary: light ? "rgba(0, 0, 0, 0.87)" : "#FAFAF9",
      secondary: light ? "rgba(0, 0, 0, 0.60)" : "#D6D3D1",
      disabled: light ? "rgba(0, 0, 0, 0.38)" : "rgba(250, 250, 249, 0.38)",
    },
    divider: light ? "rgba(0, 0, 0, 0.12)" : "rgba(250, 250, 249, 0.12)",
    nav: nav(mode),
    input: {
      outlinedBorder: light
        ? "rgba(0, 0, 0, 0.23)"
        : "rgba(250, 250, 249, 0.23)",
    },
  };
};

export const buildTheme = (mode: PaletteMode): Theme => {
  const base = createTheme({
    palette: palette(mode) as never,
    shape: { borderRadius: radius.base },
    typography: {
      fontFamily: "Roboto, Helvetica, Arial, sans-serif",
      h4Bold: { fontSize: "2.125rem", fontWeight: 700, lineHeight: 1.235 },
      subtitle1Medium: { fontSize: "1rem", fontWeight: 500, lineHeight: 1.75 },
      buttonSmall: {
        fontSize: "0.8125rem",
        fontWeight: 500,
        lineHeight: 1.75,
        textTransform: "uppercase",
      },
      buttonLarge: {
        fontSize: "0.9375rem",
        fontWeight: 500,
        lineHeight: 1.75,
        textTransform: "uppercase",
      },
      chip: { fontSize: "0.8125rem", fontWeight: 400, lineHeight: 1.385 },
      captionBold: { fontSize: "0.75rem", fontWeight: 700, lineHeight: 1.66 },
    },
  });

  return createTheme(base, {
    radius,
    border,
    iconSize,
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: radius.medium, textTransform: "uppercase" },
          sizeSmall: base.typography.buttonSmall,
          sizeLarge: base.typography.buttonLarge,
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: radius.medium },
          label: base.typography.chip,
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: { height: border.focus },
        },
      },
      MuiPaper: {
        styleOverrides: {
          rounded: { borderRadius: radius.medium },
          outlined: { borderColor: base.palette.divider },
        },
      },
      MuiCard: {
        defaultProps: { elevation: 0, variant: "outlined" },
        styleOverrides: {
          root: { borderRadius: radius.medium },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: { borderRadius: radius.medium },
          notchedOutline: { borderColor: base.palette.input.outlinedBorder },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: base.palette.nav.surface,
            color: base.palette.nav.text,
            backgroundImage: "none",
            borderBottom: `${border.accent}px solid ${base.palette.nav.accent}`,
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: base.palette.nav.surface,
            color: base.palette.nav.text,
            backgroundImage: "none",
            borderRight: `${border.thin}px solid ${base.palette.nav.divider}`,
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: radius.medium,
            "&:hover": { backgroundColor: base.palette.nav.hover },
            "&.Mui-selected": {
              backgroundColor: base.palette.nav.selected,
              "&:hover": { backgroundColor: base.palette.nav.selected },
            },
            "&.SisocNav-section.Mui-selected": {
              backgroundColor: base.palette.nav.surfaceSelected,
              "&:hover": { backgroundColor: base.palette.nav.surfaceSelected },
            },
          },
        },
      },
      MuiListItemIcon: {
        styleOverrides: {
          root: { color: "inherit", minWidth: 36 },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: { borderRadius: radius.medium },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: { fontWeight: 500, whiteSpace: "nowrap" },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            "&:hover": {
              backgroundColor: alpha(base.palette.text.primary, 0.04),
            },
          },
        },
      },
    },
  });
};

export default buildTheme;
