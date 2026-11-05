import { Component, type ErrorInfo, type ReactNode } from "react";
import { Alert, Button, Stack } from "@mui/material";
import { reportFrontendError } from "@sisoc/api";

/**
 * Un error de render no desmonta toda la app: muestra el aviso en la pantalla
 * afectada y se reinicia al cambiar de ruta (incluido el botón Atrás).
 */
export class ScreenBoundary extends Component<{ resetKey: string; children: ReactNode }, { error?: Error }> {
  state: { error?: Error } = {};

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info.componentStack);
    reportFrontendError(error, { componentStack: info.componentStack });
  }

  componentDidUpdate(previous: { resetKey: string }) {
    if (this.state.error && previous.resetKey !== this.props.resetKey) this.setState({ error: undefined });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return <Stack spacing={2} sx={{ p: { xs: 2, md: 3 }, alignItems: "flex-start" }}>
      <Alert severity="error" sx={{ alignSelf: "stretch" }}>No se pudo mostrar esta pantalla. Volvé a intentarlo; si el problema sigue, avisá a soporte.</Alert>
      <Stack direction="row" spacing={2}>
        <Button variant="outlined" onClick={() => window.history.back()}>Volver</Button>
        <Button onClick={() => this.setState({ error: undefined })}>Reintentar</Button>
      </Stack>
    </Stack>;
  }
}
