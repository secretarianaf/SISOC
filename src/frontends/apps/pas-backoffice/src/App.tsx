import { useState } from "react";
import { Alert, Box, Button, ButtonBase, Collapse, List, ListItemButton, ListItemIcon, ListItemText, Stack, Typography } from "@mui/material";
import ArrowBack from "@mui/icons-material/ArrowBack";
import Apps from "@mui/icons-material/Apps";
import Settings from "@mui/icons-material/Settings";
import ChevronRight from "@mui/icons-material/ChevronRight";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Logout from "@mui/icons-material/Logout";
import SubdirectoryArrowRight from "@mui/icons-material/SubdirectoryArrowRight";
import { useQuery } from "@tanstack/react-query";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import { leerCookie } from "@sisoc/api";
import { V2Layout } from "@sisoc/ui";
import { pasGet, webGet, type Cruces } from "./api";
import { Cargando, ErrorPas } from "./Estado";
import { TitularFormPage } from "./Gestion";
import { ImportarTitularesPage } from "./ImportarTitulares";
import { InformeDetallePage, InformeGenerarPage } from "./Informes";
import { PadronPage } from "./Titulares";
import { BuscadorPage } from "./Buscador";
import { CrucesPage, DashboardPage, FormacionPage, InformesPage, LiquidacionPage } from "./Circuitos";
import { CursosPage } from "./Cursos";

/** Tarjetas 01 a 04 del Panel de control, con los textos de Figma. */
const circuitos = [
  { path: "", title: "Panel de Control", description: "Titulares y ABM" },
  { path: "formacion", title: "Formación FCH", description: "Condicionalidad" },
  { path: "cruces", title: "Cruces y Novedades", description: "Incompatibilidades" },
  { path: "liquidacion", title: "Liquidación", description: "Nómina de pago" },
];

/** Rutas que pertenecen al Panel de control y muestran las tarjetas 01 a 04. */
function esPanel(pathname: string) {
  return pathname === "/" || pathname.startsWith("/titulares") || circuitos.some(({ path }) => path && pathname === `/${path}`);
}

/**
 * `Sisoc/Navigation card`: superficie `nav.surface`; la seleccionada pasa a
 * `nav.surfaceSelected` y el número a `nav.accent`, sin velo.
 */
const CLAVE_TITULAR = "pas-titular-seleccionado";

/**
 * Titular en foco entre Panel y Formación: sale de `/titulares/:id` o de
 * `?persona=` y se recuerda en la sesión del navegador para los cambios de módulo.
 */
function useTitularSeleccionado() {
  const { pathname, search } = useLocation();
  const id = /^\/titulares\/(\d+)/.exec(pathname)?.[1] ?? (pathname === "/formacion" ? new URLSearchParams(search).get("persona") : null);
  if (id) {
    try { sessionStorage.setItem(CLAVE_TITULAR, id); } catch { /* sin almacenamiento: solo la URL */ }
    return id;
  }
  try { return sessionStorage.getItem(CLAVE_TITULAR); } catch { return null; }
}

function destinoCircuito(path: string, titular: string | null) {
  if (!titular) return path ? `/${path}` : "/";
  if (path === "formacion") return `/formacion?${new URLSearchParams({ persona: titular })}`;
  return path ? `/${path}` : `/titulares/${titular}`;
}

function CircuitosNav() {
  const { pathname } = useLocation();
  const titular = useTitularSeleccionado();
  const cruces = useQuery({ queryKey: ["pas", "cruces/"], queryFn: () => pasGet<Cruces>("cruces/"), staleTime: 5 * 60 * 1000, retry: false });
  const alertas: Record<string, number> = { cruces: cruces.data?.incompatibilidades?.length ?? 0 };
  return <Box component="nav" aria-label="Circuitos PAS" sx={{ display: "grid", gap: 1,
    gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", lg: "repeat(4, minmax(0, 1fr))" } }}>
    {circuitos.map(({ path, title, description }, index) => {
      const selected = path ? pathname === `/${path}` : pathname === "/" || pathname.startsWith("/titulares");
      const contador = alertas[path] ?? 0;
      return <ButtonBase key={title} component={Link} to={destinoCircuito(path, titular)} aria-current={selected ? "page" : undefined}
        sx={(theme) => ({ display: "flex", flexDirection: "column", alignItems: "stretch", position: "relative", minHeight: 118, px: 2, pt: 1.5, pb: 2,
          textAlign: "left", bgcolor: selected ? "nav.surfaceSelected" : "nav.surface", color: "nav.text", overflow: "hidden",
          borderTop: `${theme.border.accent}px solid ${theme.palette.secondary.main}`, borderRadius: `${theme.radius.large}px`,
          "&:hover": { backgroundImage: `linear-gradient(${theme.palette.nav.hover}, ${theme.palette.nav.hover})` },
          "&.Mui-focusVisible": { outline: `${theme.border.focus}px solid ${theme.palette.nav.accent}`, outlineOffset: 2 } })}>
        <Typography variant="h6" component="span" sx={{ color: selected ? "nav.accent" : "nav.text", lineHeight: "32px" }}>{String(index + 1).padStart(2, "0")}</Typography>
        <Typography variant="subtitle2" component="span" sx={{ pt: 1 }}>{title}</Typography>
        <Typography variant="caption" component="span" sx={{ pt: 0.5, color: "nav.textMuted" }}>{description}</Typography>
        {contador > 0 && <Box component="span" aria-label={`${contador} alertas`} sx={{ position: "absolute", top: 12, right: 16, minWidth: 20, height: 20, px: 0.5,
          borderRadius: 9999, bgcolor: "warning.main", color: "warning.contrastText", typography: "caption", lineHeight: "20px", textAlign: "center" }}>{contador}</Box>}
      </ButtonBase>;
    })}
  </Box>;
}

type EnlacePas = { label: string; to: string; active: boolean };

/** Enlaces de tercer nivel del sidebar (Figma: 40px, flecha de subnivel). */
function EnlacesPas({ links, close }: { links: EnlacePas[]; close: () => void }) {
  return <List disablePadding>
    {links.map(({ label, to, active }) => <ListItemButton key={to} component={Link} to={to} selected={active}
      aria-current={active ? "page" : undefined} onClick={close} sx={{ pl: 6, mt: 0.5, minHeight: 40 }}>
      <ListItemIcon sx={{ minWidth: 26, color: "nav.textMuted", "& .MuiSvgIcon-root": { fontSize: "14px !important" } }}><SubdirectoryArrowRight /></ListItemIcon>
      <ListItemText primary={label} />
    </ListItemButton>)}
  </List>;
}

/**
 * Sidebar de PAS v2: Módulos › PAS › tareas del módulo y Administración con
 * Buscador PAS y Cursos PAS. En v2 no se muestran los grupos de SISOC
 * (Administración del sistema y Tableros) que sí tiene v1.
 */
function MenuPas({ close }: { close: () => void }) {
  const { pathname } = useLocation();
  const [modulos, setModulos] = useState(true);
  const [pas, setPas] = useState(true);
  const [administracion, setAdministracion] = useState(true);
  const links = [
    { label: "Panel de control", to: "/", active: esPanel(pathname) },
    { label: "Dashboard", to: "/dashboard", active: pathname === "/dashboard" },
    { label: "Informes", to: "/informes", active: pathname.startsWith("/informes") },
  ];
  return <Box component="nav" aria-label="Menú de PAS">
    {/* Figma: labels en captionBold (12/700); primer nivel de 48px y el resto de 40px. */}
    <List disablePadding sx={{ pt: 1, display: "flex", flexDirection: "column", gap: 0.5, "& .MuiListItemText-primary": { typography: "captionBold" },
      "& .MuiListItemIcon-root .MuiSvgIcon-root": { fontSize: 20 } }}>
      <ListItemButton component="a" href="/inicio/" sx={{ minHeight: 48 }}>
        <ListItemIcon><ArrowBack /></ListItemIcon><ListItemText primary="Tus módulos" />
      </ListItemButton>
      <Box aria-hidden="true" sx={{ mx: 1, my: 1, borderTop: 1, borderColor: "nav.divider" }} />
      <ListItemButton className="sisoc-section" selected aria-expanded={modulos} aria-controls="pas-modulos" onClick={() => setModulos(!modulos)} sx={{ minHeight: 48 }}>
        <ListItemIcon><Apps /></ListItemIcon><ListItemText primary="Módulos" />
        {modulos ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
      </ListItemButton>
      <Collapse in={modulos} id="pas-modulos">
        <List disablePadding>
          <ListItemButton selected aria-expanded={pas} aria-controls="pas-submenu" onClick={() => setPas(!pas)} sx={{ mt: 0.5, pl: 4, minHeight: 40 }}>
            <Box aria-hidden="true" sx={{ width: 4, height: 4, bgcolor: "nav.accent", borderRadius: "50%", mr: 1.5 }} />
            <ListItemText primary="PAS" />{pas ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
          </ListItemButton>
          <Collapse in={pas} id="pas-submenu"><EnlacesPas links={links} close={close} /></Collapse>
        </List>
      </Collapse>
      <ListItemButton aria-expanded={administracion} aria-controls="pas-administracion" onClick={() => setAdministracion(!administracion)} sx={{ minHeight: 48 }}>
        <ListItemIcon><Settings /></ListItemIcon><ListItemText primary="Administración" />
        {administracion ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
      </ListItemButton>
      <Collapse in={administracion} id="pas-administracion">
        <EnlacesPas close={close} links={[
          { label: "Buscador PAS", to: "/buscador", active: pathname === "/buscador" || pathname.startsWith("/buscador/") },
          { label: "Cursos PAS", to: "/cursos", active: pathname === "/cursos" },
        ]} />
      </Collapse>
    </List>
  </Box>;
}

function CerrarSesion() {
  return <Box component="form" method="post" action="/logout">
    <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") || ""} />
    <ListItemButton component="button" type="submit" sx={{ width: "100%", minHeight: 48 }}>
      <ListItemIcon><Logout sx={{ fontSize: 20 }} /></ListItemIcon>
      <ListItemText primary="Cerrar sesión" slotProps={{ primary: { variant: "captionBold" } }} />
    </ListItemButton>
  </Box>;
}

export default function App() {
  const { pathname } = useLocation();
  const session = useQuery({
    queryKey: ["pas-session"],
    queryFn: () => webGet<{ user: { display_name: string }; access: { state: string; required_action_url: string | null } }>("web/session/"),
  });
  if (session.isPending) return <Cargando />;
  if (session.isError) return <ErrorPas error={session.error} />;
  if (session.data.access.state !== "ready") {
    return <Alert severity="warning">Revisá los requisitos de tu cuenta para continuar. <a href="/inicio/">Volver a SISOC</a></Alert>;
  }
  return <V2Layout username={session.data.user.display_name} sectionLabel="PAS" sidebarWidth={230}
    modules={[]} navigation={(close) => <MenuPas close={close} />} sidebarFooter={<CerrarSesion />}>
    {/* Como en Figma, el contenido ocupa todo el ancho junto al menú (sin tope ni centrado). */}
    <Stack component="main" spacing={{ xs: 2, md: 3 }} sx={{ p: { xs: 2, md: 3 } }}>
      <Button href="/inicio/" variant="outlined" size="large" sx={{ alignSelf: "flex-start", minWidth: 107 }}>Volver</Button>
      {esPanel(pathname) && <CircuitosNav />}
      <Routes>
        <Route index element={<PadronPage />} />
        <Route path="titulares" element={<PadronPage />} />
        <Route path="titulares/nuevo" element={<TitularFormPage />} />
        <Route path="titulares/importar" element={<ImportarTitularesPage />} />
        <Route path="titulares/:id/editar" element={<TitularFormPage />} />
        <Route path="titulares/:id" element={<PadronPage />} />
        <Route path="buscador" element={<BuscadorPage />} />
        <Route path="buscador/nuevo" element={<TitularFormPage volver="/buscador" />} />
        <Route path="buscador/importar" element={<ImportarTitularesPage volver="/buscador" volverTexto="Volver al Buscador" />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="formacion" element={<FormacionPage />} />
        <Route path="cruces" element={<CrucesPage />} />
        <Route path="liquidacion" element={<LiquidacionPage />} />
        <Route path="informes" element={<InformesPage />} />
        <Route path="informes/generar" element={<InformeGenerarPage />} />
        <Route path="informes/:id" element={<InformeDetallePage />} />
        <Route path="cursos" element={<CursosPage />} />
        <Route path="*" element={<Alert severity="info">La página solicitada no existe en PAS. <Link to="/">Volver al panel</Link></Alert>} />
      </Routes>
    </Stack>
  </V2Layout>;
}
