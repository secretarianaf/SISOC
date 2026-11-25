/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its validators live with the screens. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { leerCookie } from "@sisoc/api";
import type { RequiredPasswordPresentation } from "../RequiredPasswordChange";
import { safeInternalPath } from "../webAccess";
import { navigation, postOnce, presentationValid, record } from "./userImport";

/**
 * `user/user_confirm_delete.html` and `user_confirm_active.html`
 * (`components/delete_confirm.html`): one confirmation, one native POST. The
 * server decides the object (scope included) and whether the actor may change
 * its state; an unconfirmed outcome is reported and never resent.
 */
export type UsuarioEstadoData = {
  title: string;
  message: string;
  object_name: string;
  confirm_text: string;
  confirm_class: string;
  cancel_url: string;
  presentation: RequiredPasswordPresentation;
};

export function usuarioEstadoValid(v: unknown): v is UsuarioEstadoData {
  return record(v) && presentationValid(v.presentation) &&
    ["title", "message", "object_name", "confirm_text", "confirm_class"].every((k) => typeof v[k] === "string") &&
    safeInternalPath(v.cancel_url) !== null;
}

export function UsuarioEstadoContent({ data, endpoint, onForbidden }: { data: UsuarioEstadoData; endpoint: string; onForbidden: (data: unknown) => void }) {
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const busy = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    const result = await postOnce(endpoint, new URLSearchParams(), "/usuarios/");
    if (!mounted.current) return;
    if (result.kind === "redirect") navigation.assign(result.to);
    else if (result.kind === "forbidden") onForbidden(result.data);
    else { setUncertain(true); setPending(false); }
  }
  return (
    <div className="error-page mt-5 px-3">
      <div className="error-content">
        <h3><i className="fas fa-exclamation-triangle text-danger px-2" />{" "}{data.title}</h3>
        <p>{data.message}{" "}<span className="font-weight-bold">{data.object_name}</span>?</p>
        <div className="text-left">
          <form method="post" onSubmit={submit}>
            <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />
            <button type="submit" className={`btn ${data.confirm_class} btn-sm`} disabled={pending || uncertain}>{data.confirm_text}</button>{" "}
            <a href={safeInternalPath(data.cancel_url) ?? "/usuarios/"} className="btn btn-secondary btn-sm">Cancelar</a>
            {uncertain && <p role="alert" className="mt-3 mb-0">No se pudo confirmar el resultado. Revise el listado antes de reintentar.</p>}
          </form>
        </div>
      </div>
    </div>
  );
}
