/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screens live here with the route. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import { NativeToasts } from "./nativeParity";
import { internal, record, renderMain, text, useMainResource } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * AD02.01 technical-report detail (`comedores/admision/informe_tecnico/<tipo>/<pk>/ver/`),
 * with the native template's markup. Data comes from
 * `/api/web/comedores/admisiones/informes/<tipo>/<pk>/`, which runs the native view.
 * The upload of the edited DOCX and the review (status change, fields to fix) keep
 * posting to the native URL, whose own rules decide; DOCX/PDF files stay backend-made.
 */
type Params = { tipo: string; id: string };
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Enlace = { kind: "docx_editado" | "docx_final"; url: string };
type InformeData = {
  id: number; tipo: string; estado: string; comedor: string; observaciones_subsanacion: string;
  campos: { nombre: string; valor: string }[];
  archivos: { docx_descargar: string | null; docx_editado_ver: string | null; pdf_final: string | null; borrador: Enlace | null };
  puede_cambiar_estado: boolean; puede_subsanar: boolean;
  urls: { admision: string; accion: string }; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const int = (v: unknown): v is number => typeof v === "number" && Number.isSafeInteger(v);
const fileUrl = (v: unknown): v is string => internal(v) || (text(v) && /^https?:\/\//.test(v));
const nullableUrl = (v: unknown) => v === null || fileUrl(v);
const informeValid = (v: unknown): v is InformeData => record(v) && int(v.id) &&
  ["tipo", "estado", "comedor", "observaciones_subsanacion"].every((k) => text(v[k])) &&
  Array.isArray(v.campos) && v.campos.every((c) => record(c) && text(c.nombre) && text(c.valor)) &&
  record(v.archivos) && ["docx_descargar", "docx_editado_ver", "pdf_final"].every((k) => nullableUrl((v.archivos as Record<string, unknown>)[k])) &&
  ((v.archivos as Record<string, unknown>).borrador === null || (record((v.archivos as Record<string, unknown>).borrador) &&
    ["docx_editado", "docx_final"].includes(((v.archivos as Record<string, unknown>).borrador as Record<string, unknown>).kind as string) &&
    fileUrl(((v.archivos as Record<string, unknown>).borrador as Record<string, unknown>).url))) &&
  typeof v.puede_cambiar_estado === "boolean" && typeof v.puede_subsanar === "boolean" &&
  record(v.urls) && internal(v.urls.admision) && internal(v.urls.accion) &&
  Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));

/** `{% csrf_token %}` of the native forms (the entry sets the cookie). */
function Csrf() {
  return <input type="hidden" name="csrfmiddlewaretoken" value={leerCookie("csrftoken") ?? ""} />;
}

/** The native Bootstrap modal (`modal fade` + backdrop), closed with the button, the backdrop or Escape. */
function Modal({ id, title, close, children }: { id: string; title: string; close: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    document.body.classList.add("modal-open");
    dialog.current?.focus();
    // Bootstrap's focus trap: Tab and Shift+Tab cycle inside the open modal.
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
      if (event.key !== "Tab" || !dialog.current) return;
      const items = [...dialog.current.querySelectorAll<HTMLElement>("a[href], button:not(:disabled), input:not([type=hidden]):not(:disabled), select, textarea")];
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1], active = document.activeElement;
      if (!dialog.current.contains(active) || (event.shiftKey && (active === first || active === dialog.current)) || (!event.shiftKey && active === last)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.body.classList.remove("modal-open"); document.removeEventListener("keydown", onKey); };
  }, [close]);
  return <>
    <div ref={dialog} className="modal fade show" id={id} tabIndex={-1} aria-labelledby={`${id}Label`} aria-modal="true" role="dialog"
      style={{ display: "block" }} onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="modal-dialog"><div className="modal-content">
        <div className="modal-header">
          <h5 className="modal-title" id={`${id}Label`}>{title}</h5>
          <button type="button" className="btn-close" aria-label="Cerrar" onClick={close} />
        </div>
        {children}
      </div></div>
    </div>
    <div className="modal-backdrop fade show" />
  </>;
}

function UploadModal({ data, close }: { data: InformeData; close: () => void }) {
  return <Modal id="subirDocxModal" title="Subir DOCX Editado" close={close}>
    <form method="post" encType="multipart/form-data" action={data.urls.accion}>
      <Csrf />
      <input type="hidden" name="informe_id" value={data.id} />
      <div className="modal-body">
        <div className="mb-3">
          <label htmlFor="docx_editado" className="form-label">Archivo DOCX editado</label>
          <input type="file" className="form-control" id="docx_editado" name="docx_editado" accept=".docx" required />
          <div className="form-text">Seleccione el archivo DOCX que editó manualmente.</div>
        </div>
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
        <button type="submit" name="subir_docx" className="btn btn-primary">Subir Archivo</button>
      </div>
    </form>
  </Modal>;
}

/** The status modal, with the checks of the page's inline script. */
function StateModal({ data, marcados, close }: { data: InformeData; marcados: string[]; close: () => void }) {
  const [estado, setEstado] = useState("");
  const [observacion, setObservacion] = useState("");
  const [fallo, setFallo] = useState<string | null>(null);
  const subsanar = estado === "A subsanar";
  const sinMarcar = subsanar && marcados.length === 0;
  const mostrarObservacion = subsanar && marcados.length > 0;
  const error = sinMarcar ? "Debe marcar al menos un campo para subsanar." : fallo;
  const alEnviar = (event: FormEvent<HTMLFormElement>) => {
    if (subsanar && observacion.trim() === "") {
      event.preventDefault();
      setFallo("Debe completar el campo de observaciones.");
    }
  };
  return <Modal id="cambiarEstadoModal" title="Cambiar estado del informe" close={close}>
    <form method="post" action={data.urls.accion} onSubmit={alEnviar}>
      <Csrf />
      <div className="modal-body">
        <div className="mb-3">
          <label htmlFor="estado" className="form-label">Nuevo estado</label>
          <select className="form-select" id="estado" name="estado" required value={estado} onChange={(e) => { setEstado(e.target.value); setFallo(null); }}>
            <option value="">Seleccione un estado</option>
            <option value="A subsanar">A subsanar</option>
            <option value="Validado">Validado</option>
          </select>
        </div>
        {mostrarObservacion && <div className="mb-3" id="observacion-container">
          <label htmlFor="observacion" className="form-label">Observaciones</label>
          <textarea className="form-control" id="observacion" name="observacion" rows={3} value={observacion} onChange={(e) => setObservacion(e.target.value)} />
        </div>}
        {error !== null && subsanar && <div className="mb-3 h6 d-flex justify-content-center align-items-center text-center" id="observacion-error">
          <i className="bi bi-x-circle-fill text-danger me-1" /> {error}
        </div>}
        {subsanar && marcados.map((campo) => <input key={campo} type="hidden" name="campos_a_subsanar" value={campo} />)}
      </div>
      <div className="modal-footer">
        <button type="button" className="btn btn-secondary" onClick={close}>Cancelar</button>
        <button type="submit" className="btn btn-primary" disabled={sinMarcar}>Guardar</button>
      </div>
    </form>
  </Modal>;
}

function Acciones({ data, abrir }: { data: InformeData; abrir: (modal: "docx" | "estado") => void }) {
  const { archivos: a } = data;
  const borrador = a.borrador;
  return <div className="row justify-content-between d-print-none mx-1 mb-3">
    <div className="col-auto">
      {a.docx_descargar !== null && <>
        <a href={a.docx_descargar} className="btn btn-success mr-1" download>📄 Descargar DOCX</a>{" "}
        <button type="button" className="btn btn-warning mr-1" onClick={() => abrir("docx")}>📤 Subir DOCX Editado</button>{" "}
      </>}
      {a.docx_editado_ver !== null && <a href={a.docx_editado_ver} className="btn btn-info mr-1" target="_blank" rel="noreferrer">📄 Ver DOCX Editado</a>}{" "}
      {data.puede_cambiar_estado && <a href="#" className="btn btn-primary mr-1" onClick={(e) => { e.preventDefault(); abrir("estado"); }}>Cambiar estado</a>}{" "}
      {a.pdf_final !== null && <a href={a.pdf_final} className="btn btn-primary" target="_blank" rel="noreferrer">&#128196; PDF Final</a>}{" "}
      {borrador?.kind === "docx_editado" && <a href={borrador.url} className="btn btn-info" target="_blank" rel="noreferrer">&#128196; DOCX Editado</a>}{" "}
      {borrador?.kind === "docx_final" && <a href={borrador.url} className="btn btn-warning" target="_blank" rel="noreferrer">&#128196; DOCX Final</a>}
    </div>
  </div>;
}

function InformePage({ data }: { data: InformeData }) {
  const [modal, setModal] = useState<"docx" | "estado" | null>(null);
  const [marcados, setMarcados] = useState<string[]>([]);
  const cerrar = () => setModal(null);
  const alternar = (nombre: string) => setMarcados((actuales) => actuales.includes(nombre) ? actuales.filter((n) => n !== nombre) : [...actuales, nombre]);
  return <>
    {/* Toastr appends its container to the body in the native page. */}
    <NativeToasts messages={data.messages} />
    <div className="container mt-4">
      <Acciones data={data} abrir={setModal} />
      <div className="row">
        {data.observaciones_subsanacion !== "" && <div className="col-12 mb-3">
          <div className="alert alert-warning">
            <h6><i className="bi bi-exclamation-triangle-fill" /> Observaciones de Subsanación:</h6>
            <p className="mb-0">{data.observaciones_subsanacion}</p>
          </div>
        </div>}
        <div className="list-group">
          {data.campos.map((campo, i) => <div key={campo.nombre} className="list-group-item d-flex justify-content-between align-items-center">
            <div><h6 className="mb-1">{campo.nombre}</h6><p className="mb-1">{campo.valor}</p></div>
            {data.puede_subsanar && <div className="form-check">
              <input className="form-check-input campo-subsanar" type="checkbox" name="campos_subsanar" value={campo.nombre} id={`check_${i + 1}`}
                checked={marcados.includes(campo.nombre)} onChange={() => alternar(campo.nombre)} />
              <label className="form-check-label" htmlFor={`check_${i + 1}`}>Subsanar</label>
            </div>}
          </div>)}
        </div>
      </div>
    </div>
    {modal === "docx" && <UploadModal data={data} close={cerrar} />}
    {modal === "estado" && <StateModal data={data} marcados={marcados} close={cerrar} />}
  </>;
}

function InformeRoute({ tipo, id }: Params) {
  const [state] = useMainResource(`web/comedores/admisiones/informes/${tipo}/${id}/`, informeValid);
  return renderMain(state, "Cargando informe…", (data) => ({
    title: `Informe Técnico: ${data.comedor}`,
    heading: `Informe Técnico: ${data.comedor} - Estado: ${data.estado}`,
    breadcrumb: <ol className="breadcrumb float-sm-right">
      <div className="breadcrumb-item"><a href={data.urls.admision}>{data.comedor}</a></div>
      <div className="breadcrumb-item active">Informe Técnico</div>
    </ol>,
    content: <InformePage data={data} />,
  }));
}

// Native GET page of `admisiones/urls/web_urls.py`, same trailing slash.
const PATH = /^\/comedores\/admision\/informe_tecnico\/([a-z]+)\/([0-9]+)\/ver\/$/;

export const admisionesInformeDetalleRoute: RouteDefinition<Params> = {
  name: "comedores-informe-tecnico-detalle",
  match(pathname) {
    const m = pathname.match(PATH);
    return m ? { tipo: m[1], id: m[2] } : null;
  },
  render({ tipo, id }) {
    return <InformeRoute key={`${tipo}-${id}`} tipo={tipo} id={id} />;
  },
};
