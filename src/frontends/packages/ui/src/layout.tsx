import { useMemo, useState, type ReactNode } from "react";
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Drawer,
  GlobalStyles,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  ThemeProvider,
  Toolbar,
  Typography,
  alpha,
  useMediaQuery,
} from "@mui/material";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import AppsIcon from "@mui/icons-material/Apps";
import { getTheme } from "./theme";
import "@fontsource/roboto/latin-300.css";
import "@fontsource/roboto/latin-400.css";
import "@fontsource/roboto/latin-500.css";
import "@fontsource/roboto/latin-700.css";

export type V2Module = { label: string; href: string; active?: boolean; icon?: ReactNode; onNavigate?: () => void };

function initialMode(): "light" | "dark" {
  try {
    return localStorage.getItem("app.theme") === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function V2Layout({ children, modules, username, sectionLabel = "Módulos" }: { children: ReactNode; modules: V2Module[]; username?: string; sectionLabel?: string }) {
  const [mode, setMode] = useState<"light" | "dark">(initialMode);
  const [menuOpen, setMenuOpen] = useState(false);
  const [accountAnchor, setAccountAnchor] = useState<HTMLElement | null>(null);
  const theme = useMemo(() => getTheme(mode), [mode]);
  const smallScreen = useMediaQuery(theme.breakpoints.down("md"));
  const accountInitials = username?.trim().split(/[\s._-]+/).filter(Boolean).map((part) => part[0]).slice(0, 2).join("").toUpperCase();

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
        "--primary-light": theme.palette.primary.light,
        "--primary-text": theme.palette.primary.text,
        "--primary-contrast": theme.palette.primary.contrastText,
        "--secondary": theme.palette.secondary.main,
        "--secondary-dark": theme.palette.secondary.dark,
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
    <AppBar position="fixed" sx={{ zIndex: (value) => value.zIndex.drawer + 1, overflow: "hidden" }}>
      <Box aria-hidden="true" sx={{ position: "absolute", inset: 0, left: { xs: "25%", md: 250 }, right: { xs: 0, md: 88 }, pointerEvents: "none", opacity: 0.18, backgroundImage: 'url("/static/custom/img/sisoc_header_texture.png")', backgroundRepeat: "no-repeat", backgroundPosition: "left center", backgroundSize: "auto 123px", filter: "brightness(0) invert(1)", maskImage: "linear-gradient(90deg, transparent, #000 30%, #000 70%, transparent)", WebkitMaskImage: "linear-gradient(90deg, transparent, #000 30%, #000 70%, transparent)" }} />
      <Toolbar sx={{ position: "relative", gap: 1.5, minHeight: "82px !important", px: { xs: 2, md: 5 } }}>
        {smallScreen && <IconButton onClick={() => setMenuOpen(true)} color="inherit" aria-label="Abrir módulos"><MenuIcon /></IconButton>}
        <Box component="a" href="/" aria-label="Ir a SISOC" sx={{ display: "flex", alignItems: "center", flexGrow: 1, minWidth: 0 }}>
          <Box component="img" src="/static/custom/img/sisoc_logo_header.png" alt="SISOC" sx={{ width: 145, height: 40, objectFit: "contain", flexShrink: 0 }} />
        </Box>
        {username && <>
          <IconButton color="inherit" size="large" sx={{ p: 0 }} aria-label="Menú de usuario" aria-controls={accountAnchor ? "v2-account-menu" : undefined} aria-haspopup="true" aria-expanded={!!accountAnchor} onClick={(event) => setAccountAnchor(event.currentTarget)}>
            <Avatar sx={{ width: 40, height: 40, bgcolor: "grey.400", color: "grey.900", fontSize: 20, fontWeight: 500 }}>{accountInitials}</Avatar>
          </IconButton>
          <Menu id="v2-account-menu" anchorEl={accountAnchor} open={!!accountAnchor} onClose={() => setAccountAnchor(null)}>
            <Box sx={{ px: 2, py: 1, minWidth: 170 }}><Typography variant="caption" color="text.secondary">Usuario</Typography><Typography variant="body2" sx={{ fontWeight: 700 }}>{username}</Typography></Box>
            <MenuItem component="a" href="/" onClick={() => setAccountAnchor(null)}>Volver a SISOC</MenuItem>
          </Menu>
        </>}
        <IconButton color="inherit" onClick={toggleMode} aria-label={mode === "light" ? "Activar modo oscuro" : "Activar modo claro"} title={mode === "light" ? "Activar modo oscuro" : "Activar modo claro"}>
          {mode === "light" ? <DarkModeOutlinedIcon /> : <LightModeOutlinedIcon />}
        </IconButton>
      </Toolbar>
    </AppBar>
    <Drawer
      variant={smallScreen ? "temporary" : "permanent"}
      open={smallScreen ? menuOpen : true}
      onClose={() => setMenuOpen(false)}
      sx={{ width: smallScreen ? 0 : 240, flexShrink: 0, "& .MuiDrawer-paper": { width: 240, boxSizing: "border-box", pt: smallScreen ? 1 : "82px", display: "flex" } }}
    >
      <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", px: 1 }}>
        <Typography variant="overline" sx={{ color: "nav.textMuted", px: 2 }}>{sectionLabel}</Typography>
        <List aria-label={sectionLabel}>
          {modules.map((item) => <ListItemButton
            key={item.href}
            className="sisoc-section"
            component="a"
            href={item.href}
            aria-current={item.active ? "page" : undefined}
            onClick={(event) => {
              if (item.onNavigate && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
                event.preventDefault();
                item.onNavigate();
                setMenuOpen(false);
              }
            }}
            selected={item.active}
          ><ListItemIcon sx={{ minWidth: 0, mr: 1.5, "& svg": { fontSize: (value) => value.iconSize.small } }}>{item.icon ?? <AppsIcon />}</ListItemIcon><ListItemText primary={item.label} /></ListItemButton>)}
        </List>
      </Box>
      <Box sx={{ p: 1, borderTop: (value) => `${value.border.thin}px solid ${value.palette.nav.divider}` }}>
        <ListItemButton component="a" href="/">
          <HomeOutlinedIcon sx={{ mr: 1, fontSize: (value) => value.iconSize.small }} />
          <ListItemText primary="Volver a SISOC" />
        </ListItemButton>
      </Box>
    </Drawer>
    <Box component="div" sx={{ ml: smallScreen ? 0 : "240px", pt: "82px", minHeight: "100vh", bgcolor: "background.default", display: "flex", flexDirection: "column" }}>
      <Box sx={{ flex: 1 }}>{children}</Box>
      <Box component="footer" sx={{ minHeight: 120, py: 3, display: "flex", justifyContent: "center", alignItems: "center", bgcolor: "nav.surface", borderTop: (value) => `${value.border.accent}px solid ${value.palette.secondary.main}` }}>
        <Box component="img" src="/static/custom/img/Presidencia_footer.svg" alt="Ministerio de Capital Humano" sx={{ width: 189, height: 72, objectFit: "contain" }} />
      </Box>
    </Box>
  </ThemeProvider>;
}
