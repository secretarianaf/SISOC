import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { initFrontendSentry, SinPermiso } from "@sisoc/api";
import App from "./App";
import { ScreenBoundary } from "./ErrorBoundary";

function Root() {
  const location = useLocation();
  return <ScreenBoundary resetKey={`${location.pathname}${location.search}`}><App /></ScreenBoundary>;
}

initFrontendSentry("inet");
const queryClient = new QueryClient({ defaultOptions: { queries: {
  // Sólo se reintenta un fallo de red o del servidor: un 4xx (no encontrado, sin permiso) es definitivo.
  retry: (failures, error) => {
    const status = (error as { response?: { status?: number } }).response?.status;
    return !(error instanceof SinPermiso) && (!status || status >= 500) && failures < 1;
  },
  staleTime: 30_000,
} } });
createRoot(document.getElementById("root")!).render(
  <React.StrictMode><QueryClientProvider client={queryClient}>
    <BrowserRouter><Root /></BrowserRouter>
  </QueryClientProvider></React.StrictMode>,
);
