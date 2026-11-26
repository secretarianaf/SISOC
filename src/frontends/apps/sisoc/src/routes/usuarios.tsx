/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators live with the screens. */
import { useEffect } from "react";
import InsumosAccessError from "../InsumosAccessError";
import { legacyIdentityFrame, userJobsFrame } from "../identityFrames";
import { prerequisiteFromForbidden } from "../webAccess";
import { useWebResource } from "./userImport";
import { UsuariosListContent, usuariosListValid } from "./usuariosList";
import { UsuarioFormContent, usuarioFormValid } from "./usuariosForm";
import { UsuarioEstadoContent, usuarioEstadoValid } from "./usuariosState";
import type { RouteDefinition } from "./types";

/**
 * Users (#2785, U06): the list (`/usuarios/`) and the activate/deactivate
 * confirmations. Business access, scope and the state change stay native.
 */
/** AdminLTE marks the native body `app-loaded` once its script runs. */
function AppLoaded() {
  useEffect(() => {
    const had = document.body.classList.contains("app-loaded");
    document.body.classList.add("app-loaded");
    return () => { if (!had) document.body.classList.remove("app-loaded"); };
  }, []);
  return null;
}

const LIST_ENDPOINT = "web/users/list/";

function UsuariosList() {
  const [state] = useWebResource(LIST_ENDPOINT + window.location.search, usuariosListValid);
  if (state.status === "loading") return <main role="status">Cargando usuarios…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el listado de usuarios.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  if (state.status !== "ready") return null;
  return <>{userJobsFrame(<UsuariosListContent data={state.data} />, state.data.presentation, "Usuarios", undefined)}<AppLoaded /></>;
}

function UsuarioEstado({ mode, id }: { mode: "deactivate" | "activate"; id: string }) {
  const endpoint = `web/users/${id}/${mode}/`;
  const [state, setState] = useWebResource(endpoint, usuarioEstadoValid);
  if (state.status === "loading") return <main role="status">Cargando usuario…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el usuario.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  if (state.status !== "ready") return null;
  const content = <UsuarioEstadoContent data={state.data} endpoint={endpoint} onForbidden={(d) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) })} />;
  return <>{legacyIdentityFrame(content, state.data.presentation, "Usuario", state.data.title)}<AppLoaded /></>;
}

function UsuarioForm({ id }: { id?: string }) {
  const endpoint = id ? `web/users/${id}/edit/` : "web/users/create/";
  const [state, setState] = useWebResource(endpoint, usuarioFormValid);
  if (state.status === "loading") return <main role="status">Cargando usuario…</main>;
  if (state.status === "error") return <main role="alert">No se pudo cargar el usuario.</main>;
  if (state.status === "forbidden") return <InsumosAccessError prerequisite={state.prerequisite} />;
  if (state.status !== "ready") return null;
  const breadcrumb = <ol className="breadcrumb float-sm-right "><li className="breadcrumb-item ">Administración</li><li className="breadcrumb-item"><a href="/usuarios/">Usuarios</a></li><li className="breadcrumb-item active">Agregar</li></ol>;
  const content = <UsuarioFormContent data={state.data} endpoint={endpoint} onForbidden={(d) => setState({ status: "forbidden", prerequisite: prerequisiteFromForbidden(d) })} />;
  return <>{legacyIdentityFrame(content, state.data.presentation, "Usuarios", "Usuarios", undefined, breadcrumb)}<AppLoaded /></>;
}

type UsuariosParams = { mode: "form"; id?: string } | { mode: "list" } | { mode: "deactivate" | "activate"; id: string };

export const usuariosRoute: RouteDefinition<UsuariosParams> = {
  name: "usuarios",
  match(pathname) {
    if (pathname === "/usuarios/") return { mode: "list" };
    if (pathname === "/usuarios/crear/") return { mode: "form" };
    const edit = pathname.match(/^\/usuarios\/editar\/([0-9]+)\/$/);
    if (edit) return { mode: "form", id: edit[1] };
    const state = pathname.match(/^\/usuarios\/(borrar|activar)\/([0-9]+)\/$/);
    return state ? { mode: state[1] === "borrar" ? "deactivate" : "activate", id: state[2] } : null;
  },
  render: (params) => (params.mode === "form" ? <UsuarioForm key={params.id ?? "create"} id={params.id} /> : params.mode === "list" ? <UsuariosList /> : <UsuarioEstado key={`${params.mode}:${params.id}`} mode={params.mode} id={params.id} />),
};
