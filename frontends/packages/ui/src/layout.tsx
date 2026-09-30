import { useMemo, useState, type ReactNode } from "react";
import {
  AppBar,
  Box,
  CssBaseline,
  Drawer,
  GlobalStyles,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  ThemeProvider,
  Toolbar,
  Typography,
  alpha,
  useMediaQuery,
} from "@mui/material";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import MenuIcon from "@mui/icons-material/Menu";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import { getTheme } from "./theme";
import "@fontsource/roboto/latin-300.css";
import "@fontsource/roboto/latin-400.css";
import "@fontsource/roboto/latin-500.css";
import "@fontsource/roboto/latin-700.css";

export type V2Module = { label: string; href: string; active?: boolean };

function initialMode(): "light" | "dark" {
  try {
    return localStorage.getItem("app.theme") === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function V2Layout({ children, modules, username }: { children: ReactNode; modules: V2Module[]; username?: string }) {
  const [mode, setMode] = useState<"light" | "dark">(initialMode);
  const [menuOpen, setMenuOpen] = useState(false);
  const theme = useMemo(() => getTheme(mode), [mode]);
  const smallScreen = useMediaQuery(theme.breakpoints.down("md"));

  function toggleMode() {
    setMode((current) => {
      const next = current === "light" ? "dark" : "light";
      try { localStorage.setItem("app.theme", next); } catch { /* storage unavailable */ }
      return next;
    });
  }

  return <ThemeProvider theme={theme}>
    <CssBaseline />
    <GlobalStyles styles={{
      ":root": {
        "--primary": theme.palette.primary.main,
        "--primary-text": theme.palette.primary.text,
        "--primary-contrast": theme.palette.primary.contrastText,
        "--secondary": theme.palette.secondary.main,
        "--secondary-text": theme.palette.secondary.text,
        "--surface": theme.palette.background.paper,
        "--canvas": theme.palette.background.default,
        "--text": theme.palette.text.primary,
        "--muted": theme.palette.text.secondary,
        "--border": theme.palette.divider,
        "--control": theme.palette.input.outlinedBorder,
        "--nav": theme.palette.nav.surface,
        "--nav-active": theme.palette.nav.surfaceSelected,
        "--nav-text": theme.palette.nav.text,
        "--nav-text-muted": theme.palette.nav.textMuted,
        "--accent": theme.palette.nav.accent,
        "--accent-ink": theme.palette.secondary.contrastText,
        "--subtle": theme.palette.action.hover,
        "--error-surface": alpha(theme.palette.error.main, 0.12),
        "--error-border": theme.palette.error.main,
        "--error-text": theme.palette.error.text,
        "--info-text": theme.palette.info.text,
        "--radius-medium": `${theme.radius.medium}px`,
        "--radius-large": `${theme.radius.large}px`,
        "--font-family": theme.typography.fontFamily,
      },
    }} />
    <AppBar position="fixed" sx={{ zIndex: (value) => value.zIndex.drawer + 1 }}>
      <Toolbar sx={{ gap: 1 }}>
        {smallScreen && <IconButton onClick={() => setMenuOpen(true)} color="inherit" aria-label="Abrir módulos"><MenuIcon /></IconButton>}
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6">SISOC</Typography>
          <Typography variant="caption" sx={{ color: "nav.textMuted" }}>Ver para ser libre</Typography>
        </Box>
        {username && <Typography variant="body2" sx={{ mr: 1 }}>{username}</Typography>}
        <IconButton onClick={toggleMode} color="inherit" aria-label={mode === "light" ? "Activar modo oscuro" : "Activar modo claro"}>
          {mode === "light" ? <Brightness4Icon /> : <Brightness7Icon />}
        </IconButton>
      </Toolbar>
    </AppBar>
    <Drawer
      variant={smallScreen ? "temporary" : "permanent"}
      open={smallScreen ? menuOpen : true}
      onClose={() => setMenuOpen(false)}
      sx={{ width: smallScreen ? 0 : 240, flexShrink: 0, "& .MuiDrawer-paper": { width: 240, boxSizing: "border-box", pt: smallScreen ? 1 : 9, display: "flex" } }}
    >
      <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", px: 1 }}>
        <Typography variant="overline" sx={{ color: "nav.textMuted", px: 2 }}>Módulos</Typography>
        <List aria-label="Módulos Front v2">
          {modules.map((item) => <ListItemButton
            key={item.href}
            className="SisocNav-section"
            component="a"
            href={item.href}
            selected={item.active}
            sx={item.active ? { color: "nav.accent", "& .MuiListItemText-primary": { color: "nav.accent" } } : undefined}
          ><ListItemText primary={item.label} /></ListItemButton>)}
        </List>
      </Box>
      <Box sx={{ p: 1, borderTop: (value) => `${value.border.thin}px solid ${value.palette.nav.divider}` }}>
        <ListItemButton component="a" href="/">
          <HomeOutlinedIcon sx={{ mr: 1, fontSize: (value) => value.iconSize.small }} />
          <ListItemText primary="Volver a SISOC" />
        </ListItemButton>
      </Box>
    </Drawer>
    <Box component="div" sx={{ ml: smallScreen ? 0 : "240px", pt: 11, minHeight: "100vh", bgcolor: "background.default" }}>{children}</Box>
  </ThemeProvider>;
}
