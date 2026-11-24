import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@sisoc/ui";
import { iniciarObservabilidad } from "@sisoc/api";
import "@fontsource/roboto/300.css";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import { App } from "./App";
import { BASE, CANONICAL_REPORT_PATH } from "./navegacion";

const canonicalReport = window.location.pathname === CANONICAL_REPORT_PATH;

// Antes de montar nada, para que un error del arranque tambien se reporte.
iniciarObservabilidad({ modulo: "celiaquia" }, import.meta.env);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Un 403 o un 404 no se arreglan reintentando.
      retry: (fallos, error) => {
        const status = (error as { response?: { status?: number } })?.response
          ?.status;
        if (status === 403 || status === 404) return false;
        return fallos < 2;
      },
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={canonicalReport ? undefined : BASE}>
        <ThemeProvider>
          <App canonicalReport={canonicalReport} />
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
