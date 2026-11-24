import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@sisoc/ui";
import { CANONICAL_REPORT_PATH, secciones, seccionesReporteCanonico } from "./navegacion";
import { ExpedienteListPage } from "./pages/ExpedienteListPage";
import { ExpedienteFormPage } from "./pages/ExpedienteFormPage";
import { ExpedienteDetailPage } from "./pages/ExpedienteDetailPage";
import { CupoDashboardPage } from "./pages/CupoDashboardPage";
import { CupoProvinciaPage } from "./pages/CupoProvinciaPage";
import { PagoListPage } from "./pages/PagoListPage";
import { PagoDetailPage } from "./pages/PagoDetailPage";
import { ReportePage } from "./pages/ReportePage";
import { SinPermisoPage } from "./pages/SinPermisoPage";
import { CanonicalExpedientesList } from "./canonicalExpedientes";
import type { matchCanonicalScreen } from "./canonical/screens";

type AppProps = {
  canonicalReport?: boolean;
  canonicalExpedientes?: boolean;
  canonicalScreen?: ReturnType<typeof matchCanonicalScreen>;
};

export function App({ canonicalReport = false, canonicalExpedientes = false, canonicalScreen = null }: AppProps = {}) {
  if (canonicalScreen) return <canonicalScreen.Component params={canonicalScreen.params} />;
  if (canonicalExpedientes) return <CanonicalExpedientesList />;
  if (canonicalReport) {
    return (
      <AppShell modulo="Celiaquía" secciones={seccionesReporteCanonico}>
        <Routes>
          <Route path={CANONICAL_REPORT_PATH} element={<ReportePage canonical />} />
        </Routes>
      </AppShell>
    );
  }
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
        <Route path="reporte" element={<ReportePage />} />
        <Route path="sin-permiso" element={<SinPermisoPage />} />
        <Route path="*" element={<Navigate to="/expedientes" replace />} />
      </Routes>
    </AppShell>
  );
}
