/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens and validators live here with the route. */
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Breadcrumb, accepted, internal, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * Survey segmentation (`encuestas/encuesta_segmentacion.html`, `/encuestas/<id>/segmentacion/`). GET
 * `/api/web/encuestas/<id>/segmentacion/` runs `EncuestaSegmentacionView` (403 without
 * `encuestas.change_encuesta`, 404 for an unknown survey; an approval-pending survey answers the native
 * redirect to its review). Each form posts what the native form submits (`FormData` of the form itself, so
 * the disabled group list and file input stay out) to its own endpoint, which runs the native view: the
 * messages arrive verbatim and the page data is read again, as the native redirect reloads the page.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Grupo = { id: number; name: string; selected: boolean };
export type SegmentacionData = {
  id: number; titulo: string; disponible_pwa: boolean; tipo: string; grupos: Grupo[];
  destinatarios: { id: number; tipo_label: string; numero_documento: string }[];
  usuarios: { id: number; username: string; full_name: string }[];
  urls: { plantilla: string }; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const list = (v: unknown, ok: (x: unknown) => boolean) => Array.isArray(v) && v.every(ok);

export function segmentacionValid(v: unknown): v is SegmentacionData {
  return record(v) && int(v.id) && text(v.titulo) && typeof v.disponible_pwa === "boolean" && text(v.tipo) &&
    list(v.grupos, (g) => record(g) && int(g.id) && text(g.name) && typeof g.selected === "boolean") &&
    list(v.destinatarios, (d) => record(d) && int(d.id) && text(d.tipo_label) && text(d.numero_documento)) &&
    list(v.usuarios, (u) => record(u) && int(u.id) && text(u.username) && text(u.full_name)) &&
    record(v.urls) && internal(v.urls.plantilla) &&
    list(v.messages, (m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

const redirectValid = (v: unknown): v is { redirect: string } => record(v) && internal(v.redirect) && !("id" in v);

type Runner = (endpoint: string, body: FormData | URLSearchParams) => Promise<boolean>;

function TipoPanel({ data, run, busy }: { data: SegmentacionData; run: Runner; busy: boolean }) {
  const [tipo, setTipo] = useState(data.tipo === "" ? "todos_los_usuarios" : data.tipo);
  const [selected, setSelected] = useState(() => new Set(data.grupos.filter((g) => g.selected).map((g) => g.id)));
  const [search, setSearch] = useState("");
  const [pwa, setPwa] = useState(data.disponible_pwa);
  const search$ = useRef<HTMLInputElement>(null);
  const chips = useRef<HTMLUListElement>(null);
  const focusAfter = useRef<number | null>(null);
  const listado = tipo === "listado_documentos" || tipo === "listado_usuarios";
  const usuarios = tipo === "listado_usuarios";
  const term = search.trim().toLocaleLowerCase();
  const chosen = data.grupos.filter((g) => selected.has(g.id));
  const visibles = data.grupos.filter((g) => g.name.toLocaleLowerCase().includes(term)).length;

  useEffect(() => {
    if (focusAfter.current === null) return;
    const buttons = chips.current?.querySelectorAll<HTMLButtonElement>("button") ?? [];
    (buttons[Math.min(focusAfter.current, buttons.length - 1)] ?? search$.current)?.focus();
    focusAfter.current = null;
  }, [selected]);

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    void run(`web/encuestas/${data.id}/segmentacion/tipo/`, new FormData(e.currentTarget));
  };
  const radio = (id: string, value: string, icon: string, title: string, help: string) => (
    <label className="radio-card">
      <input type="radio" name="tipo" value={value} id={id} checked={tipo === value} onChange={() => setTipo(value)} />
      <span className="radio-card-body">
        <span className="radio-card-title"><i className={icon} aria-hidden={value === "grupos" ? true : undefined}></i>{title}</span>
        <span className="radio-card-help">{help}</span>
      </span>
    </label>
  );

  return (
    <div className="editor-panel">
      <div className="panel-label">
        <span className="panel-label-title"><i className="fas fa-bullseye"></i> Tipo de segmentación</span>
      </div>
      <div className="panel-body">
        <form method="post" encType="multipart/form-data" id="segmentacion-tipo-form" onSubmit={submit}>
          <input type="hidden" name="disponibilidad_pwa_presente" value="1" />
          <div className="mb-3">
            <div className="form-check form-switch">
              <input type="checkbox" className="form-check-input" id="disponible-pwa" name="disponible_pwa" aria-describedby="disponible-pwa-ayuda"
                checked={pwa} onChange={(e) => setPwa(e.target.checked)} />{" "}
              <label className="form-check-label" htmlFor="disponible-pwa">Disponible en la PWA de Espacios Comunitarios</label>
            </div>
            <p className="switch-help mt-2" id="disponible-pwa-ayuda">
              Al publicarse, también podrán responderla en la PWA los destinatarios seleccionados abajo que tengan acceso habilitado a Espacios Comunitarios.
            </p>
          </div>
          <div className="radio-cards">
            {radio("tipo-todos", "todos_los_usuarios", "fas fa-users", "Todos los usuarios logueados", "Se envía a cualquier usuario que inicie sesión en el sistema.")}
            {radio("tipo-listado", "listado_documentos", "fas fa-list-ul", "Listado de documentos", "Solo los DNI/CUIT/CUIL cargados manualmente o por archivo.")}
            {radio("tipo-usuarios", "listado_usuarios", "fas fa-user-tag", "Listado de IDs de usuarios", "Solo los usuarios de SISOC seleccionados por su ID.")}
            {radio("tipo-grupos", "grupos", "fas fa-users-cog", "Grupos de usuarios", "Usuarios que pertenezcan a cualquiera de los grupos seleccionados.")}
          </div>

          <fieldset id="grupos-field" className="mt-3" hidden={tipo !== "grupos"} disabled={tipo !== "grupos"}>
            <legend className="fs-6">Seleccioná uno o más grupos</legend>
            <p className="switch-help" id="grupos-ayuda">
              Alcanza con pertenecer a uno de los grupos elegidos. Si cambia la pertenencia de un usuario, cambia su acceso a esta encuesta.
            </p>
            <div className="grupos-seleccionados mb-3">
              <p id="grupos-contador" className="mb-2" aria-live="polite">{chosen.length}{chosen.length === 1 ? " grupo seleccionado" : " grupos seleccionados"}</p>
              <ul id="grupos-seleccionados" ref={chips} className="list-unstyled d-flex flex-wrap gap-2 mb-0" aria-label="Grupos seleccionados">
                {chosen.map((g, index) => (
                  <li key={g.id}>
                    <button type="button" className="btn-cancel grupo-seleccionado" aria-label={`Quitar grupo ${g.name}`}
                      onClick={() => { setSelected((s) => { const n = new Set(s); n.delete(g.id); return n; }); focusAfter.current = index; }}>
                      <span>{g.name}</span><span aria-hidden="true">×</span>
                    </button>
                  </li>
                ))}
              </ul>
              <p id="grupos-seleccionados-vacio" className="switch-help mb-0" hidden={chosen.length > 0}>
                Todavía no seleccionaste grupos. Marcalos en el listado de abajo.
              </p>
            </div>
            <label htmlFor="buscar-grupo">Buscar grupo</label>
            <input type="search" id="buscar-grupo" ref={search$} className="form-control mb-2" placeholder="Escribí el nombre del grupo"
              value={search} onChange={(e) => setSearch(e.target.value)} />
            <div style={{ maxHeight: 260, overflowY: "auto" }} aria-describedby="grupos-ayuda">
              {data.grupos.map((g) => (
                <label key={g.id} className={`d-flex align-items-center gap-2 py-2${g.name.toLocaleLowerCase().includes(term) ? "" : " d-none"}`} data-grupo-opcion="">
                  <input type="checkbox" className="form-check-input m-0" name="grupos" value={g.id} checked={selected.has(g.id)}
                    onChange={(e) => setSelected((s) => { const n = new Set(s); if (e.target.checked) n.add(g.id); else n.delete(g.id); return n; })} />
                  <span>{g.name}</span>
                </label>
              ))}
              {data.grupos.length === 0 && <p className="switch-help">No hay grupos disponibles.</p>}
            </div>
            <p id="grupos-sin-resultados" className="switch-help" hidden={visibles !== 0}>No hay grupos que coincidan con la búsqueda.</p>
          </fieldset>

          <div id="listado-archivo-field" className="subfields" style={{ borderTop: "none", paddingTop: 0, marginTop: 18, display: listado ? undefined : "none" }}>
            <div className="field-col" style={{ minWidth: "100%" }}>
              <div className="d-flex justify-content-between align-items-end mb-1" style={{ flexWrap: "wrap", gap: 8 }}>
                <label htmlFor="archivo_listado" className="mb-0">Reemplazar listado por archivo (Excel o CSV, opcional)</label>
                <a href={`${data.urls.plantilla}?tipo=${usuarios ? "listado_usuarios" : "listado_documentos"}`} id="descargar-plantilla" className="btn-cancel plantilla-descarga">
                  <i className="fas fa-download me-1"></i> Descargar plantilla
                </a>
              </div>
              <input type="file" className="form-control" name="archivo_listado" id="archivo_listado" accept=".xlsx,.csv" disabled={!listado} />
              <small className="form-text d-block mt-1" id="archivo-columnas">{usuarios ? "Columna requerida: usuario_id." : "Columnas requeridas: tipo_documento, numero_documento."}</small>
              <small className="form-text d-block mt-1">Si subís un archivo, reemplaza el listado actual completo. Máximo 5 MB.</small>
              <small className="form-text d-block mt-1" id="usuarios-ayuda" hidden={!usuarios}>Usá los IDs de este ambiente de SISOC; pueden corresponder a otras personas en otro ambiente. La plantilla contiene la columna usuario_id: completá un ID por fila.</small>
            </div>
          </div>

          <div className="editor-actions justify-content-end" style={{ paddingTop: 18 }}>
            <button type="submit" className="btn-save" disabled={busy}>
              <i className="fas fa-save me-1"></i> Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Destinatarios({ data, run, busy }: { data: SegmentacionData; run: Runner; busy: boolean }) {
  const porUsuario = data.tipo === "listado_usuarios";
  const add = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const body = new URLSearchParams(new FormData(form) as unknown as Record<string, string>);
    void run(`web/encuestas/${data.id}/segmentacion/agregar/`, body);
  };
  const quitar = (id: number) => (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    void run(`web/encuestas/${data.id}/segmentacion/${id}/quitar/`, new URLSearchParams());
  };
  const boton = <>
    <i className="fas fa-times"></i> Quitar
  </>;
  return (
    <>
      <div className="editor-panel">
        <div className="panel-label">
          <span className="panel-label-title"><i className="fas fa-user-plus"></i> Agregar destinatario</span>
        </div>
        <div className="panel-body">
          <form method="post" className="field-row" onSubmit={add}>
            {porUsuario ? (
              <div>
                <label htmlFor="usuario_id">ID de usuario en SISOC</label>
                <input type="number" name="usuario_id" id="usuario_id" className="form-control" min="1" step="1" required />
              </div>
            ) : (
              <>
                <div>
                  <label htmlFor="tipo_documento">Tipo</label>
                  <select name="tipo_documento" id="tipo_documento" className="form-select">
                    <option value="dni">DNI</option>
                    <option value="cuit">CUIT</option>
                    <option value="cuil">CUIL</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="numero_documento">Número</label>
                  <input type="text" name="numero_documento" id="numero_documento" className="form-control" required />
                </div>
              </>
            )}
            <div className="field-row-action">
              <button type="submit" className="btn-dashed" disabled={busy}>
                <i className="fas fa-plus"></i> Agregar
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="editor-panel">
        <div className="panel-label">
          <span className="panel-label-title"><i className="fas fa-address-book"></i> Destinatarios</span>
          <span className="count-badge"><b>{porUsuario ? data.usuarios.length : data.destinatarios.length}{" "}</b>{" "}cargados</span>
        </div>
        <div className="panel-body">
          {porUsuario ? (
            <div className="destinatarios-list">
              {data.usuarios.map((u) => (
                <div className="destinatario-row" key={u.id}>
                  <span className="destinatario-tipo">ID {u.id}</span>
                  <span className="destinatario-numero">{u.username}{u.full_name ? <>{" "}· {u.full_name}</> : null}</span>
                  <form method="post" onSubmit={quitar(u.id)}>
                    <button type="submit" className="btn-quitar-pregunta btn btn-sm" disabled={busy}>{boton}</button>
                  </form>
                </div>
              ))}
              {data.usuarios.length === 0 && <p className="switch-help mb-0">No hay usuarios cargados todavía.</p>}
            </div>
          ) : data.destinatarios.length > 0 ? (
            <div className="destinatarios-list">
              {data.destinatarios.map((d) => (
                <div className="destinatario-row" key={d.id}>
                  <span className="destinatario-tipo">{d.tipo_label}</span>
                  <span className="destinatario-numero">{d.numero_documento}</span>
                  <form method="post" onSubmit={quitar(d.id)}>
                    <button type="submit" className="btn-quitar-pregunta btn btn-sm" disabled={busy}>{boton}</button>
                  </form>
                </div>
              ))}
            </div>
          ) : (
            <p className="switch-help mb-0">No hay destinatarios cargados todavía.</p>
          )}
        </div>
      </div>
    </>
  );
}

type Setter = (data: SegmentacionData) => void;

export function SegmentacionContent({ data, reload }: { data: SegmentacionData; reload: Setter }) {
  const [busy, setBusy] = useState(false);
  const [toasts, setToasts] = useState<Message[]>(data.messages);
  const [version, setVersion] = useState(0);
  const endpoint = `web/encuestas/${data.id}/segmentacion/`;

  const run: Runner = async (url, body) => {
    setBusy(true);
    try {
      const { data: result, status } = await webClient.post(url, body, { validateStatus: accepted });
      if (status === 200 && record(result) && result.ok === true && Array.isArray(result.messages)) {
        const page = await webClient.get(endpoint, { validateStatus: accepted });
        if (page.status === 200 && segmentacionValid(page.data)) {
          setToasts(result.messages as Message[]);
          setVersion((v) => v + 1);
          reload(page.data);
          resetAfterRejectedPost();
          return true;
        }
        if (redirectValid(page.data)) { window.location.assign(page.data.redirect); return true; }
      }
      setToasts([{ message: "No se pudo completar la operación.", level: "error" }]);
    } catch {
      setToasts([{ message: "No se pudo completar la operación.", level: "error" }]);
    } finally {
      setBusy(false);
    }
    return false;
  };

  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/encuestaForm.css" />
      <link rel="stylesheet" href="/static/custom/css/encuestaSegmentacion.css" />
      <div className="encuesta-editor encuesta-segmentacion">
        <div className="d-flex justify-content-between align-items-start mb-3">
          <div>
            <h2 className="mb-1">Segmentación</h2>
            <p className="switch-help mb-0">{data.titulo}</p>
          </div>
        </div>
        <TipoPanel key={`tipo-${version}`} data={data} run={run} busy={busy} />
        {(data.tipo === "listado_documentos" || data.tipo === "listado_usuarios") && <Destinatarios key={`dest-${version}`} data={data} run={run} busy={busy} />}
      </div>
      <NativeToasts messages={toasts} />
    </>
  );
}

const pageValid = (v: unknown): v is SegmentacionData | { redirect: string } => segmentacionValid(v) || redirectValid(v);

function SegmentacionPage({ id }: { id: string }) {
  const [state, setState] = useMainResource(`web/encuestas/${id}/segmentacion/`, pageValid);
  useEffect(() => {
    if (state.status === "ready" && redirectValid(state.data)) window.location.replace(state.data.redirect);
  }, [state]);
  const reload = (data: SegmentacionData) => setState((s) => (s.status === "ready" ? { ...s, data } : s));
  return renderMain(state, "Cargando segmentación…", (data) => {
    if (!segmentacionValid(data)) return { title: "Segmentación", breadcrumb: <Breadcrumb items={[]} />, content: null };
    return {
      title: `Segmentación: ${data.titulo}`, activePath: "/encuestas/",
      breadcrumb: <Breadcrumb items={[]} />,
      content: <SegmentacionContent data={data} reload={reload} />,
    };
  });
}

export const encuestasSegmentacionRoute: RouteDefinition<{ id: string }> = {
  name: "encuestas-segmentacion",
  match(pathname) {
    const found = /^\/encuestas\/([0-9]+)\/segmentacion\/$/.exec(pathname);
    return found ? { id: found[1] } : null;
  },
  render: ({ id }) => <SegmentacionPage id={id} />,
};
