import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { statusPas } from "./api";
import App from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("Falta la raíz de PAS.");

const client = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => count < 1 && ((statusPas(error) ?? 500) >= 500),
    },
    mutations: { retry: false },
  },
});

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter basename="/v2/pas"><App /></BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
