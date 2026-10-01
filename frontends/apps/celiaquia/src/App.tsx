import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@sisoc/ui";
import { secciones } from "./navegacion";
import { ExpedienteListPage } from "./pages/ExpedienteListPage";
import { ExpedienteFormPage } from "./pages/ExpedienteFormPage";
import { ExpedienteDetailPage } from "./pages/ExpedienteDetailPage";
import { CupoDashboardPage } from "./pages/CupoDashboardPage";
import { CupoProvinciaPage } from "./pages/CupoProvinciaPage";
import { PagoListPage } from "./pages/PagoListPage";
import { PagoDetailPage } from "./pages/PagoDetailPage";
import { SinPermisoPage } from "./pages/SinPermisoPage";

export function App() {
  return (
    <AppShell modulo="Celiaquía" secciones={secciones}>
      <Routes>
        <Route path="/" element={<Navigate to="/expedientes" replace />} />
        <Route path="expedientes" element={<ExpedienteListPage />} />
        <Route path="expedientes/nuevo" element={<ExpedienteFormPage />} />
        <Route path="expedientes/:id" element={<ExpedienteDetailPage />} />
        <Route path="cupos" element={<CupoDashboardPage />} />
        <Route path="cupos/:provinciaId" element={<CupoProvinciaPage />} />
        <Route path="pagos/:provinciaId" element={<PagoListPage />} />
        <Route path="pagos/expediente/:id" element={<PagoDetailPage />} />
        <Route path="sin-permiso" element={<SinPermisoPage />} />
        <Route path="*" element={<Navigate to="/expedientes" replace />} />
      </Routes>
    </AppShell>
  );
}
