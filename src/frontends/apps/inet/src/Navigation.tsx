import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Box, Collapse, List, ListItemButton, ListItemIcon, ListItemText } from "@mui/material";
import ArrowBack from "@mui/icons-material/ArrowBack";
import Apps from "@mui/icons-material/Apps";
import ExpandMore from "@mui/icons-material/ExpandMore";
import ChevronRight from "@mui/icons-material/ChevronRight";
import SubdirectoryArrowRight from "@mui/icons-material/SubdirectoryArrowRight";
import Logout from "@mui/icons-material/Logout";
import { leerCookie, type InetSession } from "@sisoc/api";
import { ROOT } from "./data";

export function InetNavigation({ session, close }: { session?: InetSession; close: () => void }) {
  const [open, setOpen] = useState(true);
  const [inetOpen, setInetOpen] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const go = (href: string) => { navigate(href); close(); };
  return <List aria-label="Navegación INET" sx={{ pt: 1, "& .MuiListItemText-primary": { typography: "caption" } }}>
    <ListItemButton component="a" href="/" sx={{ mb: 3, borderBottom: 1, borderColor: "nav.divider", pb: 3, borderRadius: 0 }}><ListItemIcon sx={{ minWidth: 32 }}><ArrowBack fontSize="small" /></ListItemIcon><ListItemText primary="Tus módulos" /></ListItemButton>
    <ListItemButton className="sisoc-section" selected onClick={() => setOpen(!open)} aria-expanded={open}><ListItemIcon sx={{ minWidth: 32 }}><Apps fontSize="small" /></ListItemIcon><ListItemText primary="Módulos" />{open ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}</ListItemButton>
    <Collapse in={open}><List disablePadding><ListItemButton onClick={() => setInetOpen(!inetOpen)} aria-expanded={inetOpen} sx={{ bgcolor: "nav.selected", color: "nav.accent", mt: .5, pl: 3 }}><Box sx={{ width: 6, height: 6, bgcolor: "nav.accent", borderRadius: "50%", mr: 2 }} /><ListItemText primary="INET" />{inetOpen ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}</ListItemButton>
      <Collapse in={inetOpen}><List disablePadding>{[{ label: "CFP", href: `${ROOT}centros/`, active: !location.pathname.includes("/planes") }, ...(session?.puede_ver_planes ? [{ label: "Planes curriculares", href: `${ROOT}planes/`, active: location.pathname.includes("/planes") }] : [])].map((item) => <ListItemButton key={item.href} component="a" href={item.href} selected={item.active} aria-current={item.active ? "page" : undefined} onClick={(event) => { if (!event.ctrlKey && !event.metaKey && event.button === 0) { event.preventDefault(); go(item.href); } }} sx={{ pl: 5, mt: .5, "&.Mui-selected": { bgcolor: "nav.selected" } }}><ListItemIcon sx={{ minWidth: 30, color: "nav.textMuted" }}><SubdirectoryArrowRight fontSize="small" /></ListItemIcon><ListItemText primary={item.label} /></ListItemButton>)}</List></Collapse>
    </List></Collapse>
  </List>;
}

export function InetLogout() {
  return <Box component="form" method="post" action="/logout"><input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") || ""} /><ListItemButton component="button" type="submit" sx={{ width: "100%" }}><Logout sx={{ mr: 1, fontSize: 20 }} /><ListItemText primary="Cerrar Sesión" slotProps={{ primary: { variant: "caption" } }} /></ListItemButton></Box>;
}
