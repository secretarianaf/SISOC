import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import type { NavSection } from "./Sidebar";
import { Footer } from "./Footer";

export type AppShellProps = {
  modulo: string;
  secciones: NavSection[];
  iniciales?: string;
  children: ReactNode;
};

/** Marco de /v2/: propio del front nuevo, no reutiliza el sidebar viejo. */
export function AppShell({
  modulo,
  secciones,
  iniciales,
  children,
}: AppShellProps) {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Header modulo={modulo} iniciales={iniciales} />
      <Sidebar sections={secciones} />
      <Box
        component="main"
        sx={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          bgcolor: "background.default",
        }}
      >
        <Box sx={{ height: 64, flexShrink: 0 }} />
        <Container maxWidth="xl" sx={{ py: 3, flex: 1 }}>
          {children}
        </Container>
        <Footer />
      </Box>
    </Box>
  );
}
