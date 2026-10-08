import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError, initFrontendSentry } from "@sisoc/api";
import App from "./App";
import "./styles.css";

initFrontendSentry("vpsl");
const queryClient = new QueryClient({
  defaultOptions: { queries: {
    retry: (failures, error) => !(error instanceof ApiError && [401, 403, 404].includes(error.status)) && failures < 2,
  } },
});
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
