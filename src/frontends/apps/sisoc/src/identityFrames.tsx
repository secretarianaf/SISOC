import type { ReactNode } from "react";
import type { RequiredPasswordPresentation } from "./RequiredPasswordChange";
import SisocShell from "./routes/SisocShell";

// Identity pages reuse the legacy frame from their own presentation DTO, never business capabilities.
export function legacyIdentityFrame(
  content: ReactNode,
  presentation: RequiredPasswordPresentation,
  pageTitle: string,
  heading = pageTitle,
  overlays?: ReactNode,
  breadcrumb?: ReactNode,
  hideBack = false,
  backHref = "/",
  /** Path the native menu rules evaluate instead of the URL (see `SisocShell`). */
  activePath?: string,
) {
  return <SisocShell
    context={{ user: presentation.user, navigation: presentation.legacy_frame_navigation, footer_version_label: presentation.footer_version_label }}
    content={content}
    pageTitle={pageTitle}
    heading={heading}
    overlays={overlays}
    breadcrumb={breadcrumb}
    hideBack={hideBack}
    backHref={backHref}
    previewLinks={false}
    activePath={activePath}
  />;
}

export function requiredPasswordFrame(content: ReactNode, presentation: RequiredPasswordPresentation) {
  return legacyIdentityFrame(content, presentation, "Cambio obligatorio de contraseña", "Actualizar contraseña");
}

export function accountFrame(content: ReactNode, presentation: RequiredPasswordPresentation, overlays?: ReactNode) {
  return legacyIdentityFrame(content, presentation, "Mi cuenta", "Mi cuenta", overlays);
}

export function confirmationFrame(content: ReactNode, presentation: RequiredPasswordPresentation, overlays?: ReactNode) {
  return legacyIdentityFrame(content, presentation, "Confirma tus datos personales", "Confirma tus datos personales", overlays);
}

// The source home has no back button and an empty heading row.
export function homeFrame(content: ReactNode, presentation: RequiredPasswordPresentation, overlays?: ReactNode) {
  return legacyIdentityFrame(content, presentation, "", "", overlays, undefined, true);
}

// The groups list titles the page by its heading; create/edit keep "Grupos" as the document title.
export function groupsFrame(mode: "list" | "create" | "edit") {
  return (content: ReactNode, presentation: RequiredPasswordPresentation, title: string, breadcrumb?: ReactNode) =>
    legacyIdentityFrame(content, presentation, mode === "list" ? title : "Grupos", title, undefined, breadcrumb);
}

// User job pages (import, bulk credentials) title the document by their heading;
// job details go back to their native `volver_url` instead of `/`.
export function userJobsFrame(content: ReactNode, presentation: RequiredPasswordPresentation, title: string, breadcrumb: ReactNode, backHref?: string) {
  return legacyIdentityFrame(content, presentation, title, title, undefined, breadcrumb, false, backHref);
}
