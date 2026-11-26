import { useEffect } from "react";
import { safeInternalPath, type WebAccess } from "./webAccess";

function prerequisiteMessage(state: WebAccess["state"]): string {
  switch (state) {
    case "web_access_denied":
      return "Tu cuenta no tiene habilitado el acceso web.";
    case "password_change_required":
      return "Necesitás actualizar tu contraseña para continuar.";
    case "profile_confirmation_required":
      return "Necesitás confirmar tu perfil para continuar.";
    case "mandatory_survey_required":
      return "Necesitás completar la encuesta pendiente para continuar.";
    default:
      return "Antes de continuar, revisá el requisito indicado por SISOC.";
  }
}

export default function InsumosAccessError({
  prerequisite,
}: {
  prerequisite?: WebAccess | null;
}) {
  useEffect(() => {
    if (prerequisite) return undefined;
    const previousTitle = document.title;
    document.title = "SISOC - Error 403";
    return () => {
      if (document.title === "SISOC - Error 403") document.title = previousTitle;
    };
  }, [prerequisite]);

  if (prerequisite) {
    const destination = safeInternalPath(prerequisite.required_action_url) ?? "/";
    return (
      <main className="sisoc-message" role="main">
        <section className="sisoc-message-card" aria-labelledby="access-title">
          <h1 id="access-title">Antes de continuar</h1>
          <p>{prerequisiteMessage(prerequisite.state)}</p>
          <a className="sisoc-action-link" href={destination}>
            Continuar en SISOC
          </a>
        </section>
      </main>
    );
  }

  return (
    <div className="error-page align-items-center">
      <h2 className="headline text-info">403</h2>
      <div className="error-content">
        <h3>
          <i className="fas fa-exclamation-triangle text-info" aria-hidden="true" />{" "}
          ¡Ups! Algo salió mal.
        </h3>
        <p>
          No tiene permisos suficientes para realizar la acción que deseaba. Si se trata de un error, comuníquese con el administrador del sistema.
        </p>
        <p className="mt-2">
          Mientras tanto, puede <a href="/inicio/">volver al inicio</a> o intentar usar el buscador de menú.
        </p>
      </div>
    </div>
  );
}
