import { useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import DashboardIcon from "@mui/icons-material/SpaceDashboard";
import FolderIcon from "@mui/icons-material/FolderCopy";
import LogoutIcon from "@mui/icons-material/Logout";

export const SIDEBAR_WIDTH = 272;

export type NavNode = {
  label: string;
  href?: string;
  children?: NavNode[];
};

export type NavSection = {
  label: string;
  /** Modulos se filtra por la seleccion del Hub; el resto muestra todo siempre. */
  esModulos?: boolean;
  items: NavNode[];
};

function NodeItem({
  node,
  level,
  pathname,
}: {
  node: NavNode;
  level: 2 | 3;
  pathname: string;
}) {
  const [open, setOpen] = useState(true);
  const hasChildren = Boolean(node.children?.length);
  const selected = Boolean(node.href && pathname.startsWith(node.href));

  return (
    <>
      <ListItemButton
        selected={selected}
        onClick={hasChildren ? () => setOpen((v) => !v) : undefined}
        {...(hasChildren ? {} : { component: RouterLink, to: node.href ?? "" })}
        sx={{ pl: level === 2 ? 3 : 5, py: 0.75 }}
      >
        <ListItemText
          primary={node.label}
          slotProps={{
            primary: {
              variant: "body2",
              sx: { color: selected ? "nav.text" : "nav.textMuted" },
            },
          }}
        />
        {hasChildren ? (
          open ? (
            <ExpandLess fontSize="small" />
          ) : (
            <ExpandMore fontSize="small" />
          )
        ) : null}
      </ListItemButton>

      {hasChildren ? (
        <Collapse in={open} timeout="auto" unmountOnExit>
          <List component="div" disablePadding>
            {node.children!.map((child) => (
              <NodeItem
                key={child.label}
                node={child}
                level={3}
                pathname={pathname}
              />
            ))}
          </List>
        </Collapse>
      ) : null}
    </>
  );
}

export function Sidebar({ sections }: { sections: NavSection[] }) {
  const { pathname } = useLocation();
  const [abiertas, setAbiertas] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(sections.map((s) => [s.label, Boolean(s.esModulos)])),
  );

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        display: { xs: "none", md: "block" },
        "& .MuiDrawer-paper": {
          width: SIDEBAR_WIDTH,
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
        },
      }}
    >
      <Box sx={{ height: 64, flexShrink: 0 }} />

      {/* El bloque del menu scrollea; Cerrar sesion queda fuera de ese scroll. */}
      <Box sx={{ flex: 1, overflowY: "auto", px: 1, py: 1 }}>
        {sections.map((section) => {
          const open = abiertas[section.label] ?? false;
          return (
            <List key={section.label} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                className="SisocNav-section"
                selected={open}
                onClick={() =>
                  setAbiertas((s) => ({ ...s, [section.label]: !open }))
                }
              >
                <ListItemIcon>
                  {section.esModulos ? (
                    <FolderIcon fontSize="small" />
                  ) : (
                    <DashboardIcon fontSize="small" />
                  )}
                </ListItemIcon>
                <ListItemText
                  primary={section.label}
                  slotProps={{ primary: { variant: "subtitle1Medium" } }}
                />
                {open ? (
                  <ExpandLess fontSize="small" />
                ) : (
                  <ExpandMore fontSize="small" />
                )}
              </ListItemButton>

              <Collapse in={open} timeout="auto" unmountOnExit>
                <List component="div" disablePadding>
                  {section.items.map((node) => (
                    <NodeItem
                      key={node.label}
                      node={node}
                      level={2}
                      pathname={pathname}
                    />
                  ))}
                </List>
              </Collapse>
            </List>
          );
        })}
      </Box>

      <Divider sx={{ borderColor: "nav.divider" }} />
      <Box sx={{ p: 1, flexShrink: 0 }}>
        <ListItemButton component="a" href="/logout/">
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          <Typography variant="body2" sx={{ color: "nav.textMuted" }}>
            Cerrar sesión
          </Typography>
        </ListItemButton>
      </Box>
    </Drawer>
  );
}
