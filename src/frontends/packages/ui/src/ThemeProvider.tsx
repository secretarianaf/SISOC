import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ThemeProvider as MuiThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import type { PaletteMode } from "@mui/material";
import { buildTheme } from "./theme.celiaquia";

const STORAGE_KEY = "app.theme";

type ColorModeContextValue = {
  mode: PaletteMode;
  toggle: () => void;
};

const ColorModeContext = createContext<ColorModeContextValue>({
  mode: "light",
  toggle: () => {},
});

export const useColorMode = () => useContext(ColorModeContext);

/**
 * El modo por defecto es claro. La preferencia se guarda en `localStorage`,
 * siempre dentro de try/catch: en ventana privada o con las cookies bloqueadas
 * el acceso puede tirar, y la app tiene que renderizar igual.
 *
 * Como todas las apps de /v2/ comparten origen, la preferencia es comun a todas.
 */
const leerModoGuardado = (): PaletteMode => {
  try {
    const guardado = window.localStorage.getItem(STORAGE_KEY);
    return guardado === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
};

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<PaletteMode>(leerModoGuardado);

  const toggle = useCallback(() => {
    setMode((actual) => {
      const siguiente: PaletteMode = actual === "light" ? "dark" : "light";
      try {
        window.localStorage.setItem(STORAGE_KEY, siguiente);
      } catch {
        // Sin almacenamiento la preferencia dura lo que la sesion. No es un error.
      }
      return siguiente;
    });
  }, []);

  const colorMode = useMemo(() => ({ mode, toggle }), [mode, toggle]);
  const theme = useMemo(() => buildTheme(mode), [mode]);

  return (
    <ColorModeContext.Provider value={colorMode}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ColorModeContext.Provider>
  );
}
