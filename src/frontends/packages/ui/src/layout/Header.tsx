import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Avatar from "@mui/material/Avatar";
import Tooltip from "@mui/material/Tooltip";
import DarkModeIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeIcon from "@mui/icons-material/LightModeOutlined";
import { useColorMode } from "../ThemeProvider";

export type HeaderProps = {
  /** Nombre del modulo, a la derecha de la marca. */
  modulo: string;
  /** Iniciales del usuario logueado. */
  iniciales?: string;
};

export function Header({ modulo, iniciales = "—" }: HeaderProps) {
  const { mode, toggle } = useColorMode();

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}
    >
      <Toolbar sx={{ gap: 2 }}>
        <Typography variant="subtitle1Medium" sx={{ color: "nav.text" }}>
          SISOC
        </Typography>
        <Typography variant="body2" sx={{ color: "nav.textMuted" }}>
          {modulo}
        </Typography>

        <Box sx={{ flex: 1 }} />

        <Tooltip title={mode === "light" ? "Modo oscuro" : "Modo claro"}>
          <IconButton onClick={toggle} sx={{ color: "nav.text" }}>
            {mode === "light" ? <DarkModeIcon /> : <LightModeIcon />}
          </IconButton>
        </Tooltip>

        <IconButton sx={{ p: 0.5 }}>
          <Avatar
            sx={{
              width: 32,
              height: 32,
              bgcolor: "nav.accent",
              color: "rgba(0,0,0,0.87)",
            }}
          >
            <Typography variant="captionBold">{iniciales}</Typography>
          </Avatar>
        </IconButton>
      </Toolbar>
    </AppBar>
  );
}
