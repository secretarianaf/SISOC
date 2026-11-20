/* eslint-disable react-refresh/only-export-components -- route module: the validator and the navigation seam are exported for the tests. */
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { NativeToasts, resetAfterRejectedPost } from "./nativeParity";
import { internal, postForm, record, renderMain, text, useMainResource, webClient } from "./MainFrame";
import type { RouteDefinition } from "./types";

/**
 * C05.02 "Agregar familiar": `ciudadanos/grupofamiliar_form.html`. GET `/api/web/ciudadanos/<pk>/familiares/nuevo/` runs
 * `GrupoFamiliarCreateView` (404 for the ciudadano, then 403 without `change_ciudadano`) and returns what the template prints;
 * the POST sends the native fields, a rejected form comes back as 400 with the bound values and errors and a saved one as a
 * redirect to the ficha (full-page navigation, the message waits in the queue). The familiar search is the native
 * `/api/ciudadanos/buscar/` the template script calls.
 */
type Message = { message: string; level: "success" | "error" | "warning" | "info" };
type Option = { value: string; label: string };
type Values = { ciudadano_2: string; vinculo: string; estado_relacion: string; conviven: boolean; cuidador_principal: boolean; observaciones: string };
export type FamiliarData = {
  ciudadano: { id: number; texto: string; volver_url: string };
  campos: { ciudadano_2: { label: string; placeholder: string }; vinculo: { label: string; options: Option[] }; estado_relacion: { label: string; options: Option[] };
    conviven: { label: string }; cuidador_principal: { label: string }; observaciones: { label: string } };
  values: Values; errors: Record<string, string[]>; messages: Message[];
};

const LEVELS = ["success", "error", "warning", "info"];
const options = (v: unknown) => Array.isArray(v) && v.every((o) => record(o) && text(o.value) && text(o.label));
const labeled = (v: unknown) => record(v) && text(v.label);
const UNCERTAIN = "No se pudo confirmar el resultado. Revise la ficha del ciudadano antes de volver a intentar.";

export function familiarValid(v: unknown): v is FamiliarData {
  if (!record(v) || !record(v.ciudadano) || !record(v.campos) || !record(v.values) || !record(v.errors)) return false;
  const c = v.campos, x = v.values;
  return Number.isSafeInteger(v.ciudadano.id) && text(v.ciudadano.texto) && internal(v.ciudadano.volver_url) &&
    record(c.ciudadano_2) && text(c.ciudadano_2.label) && text(c.ciudadano_2.placeholder) &&
    record(c.vinculo) && text(c.vinculo.label) && options(c.vinculo.options) &&
    record(c.estado_relacion) && text(c.estado_relacion.label) && options(c.estado_relacion.options) &&
    labeled(c.conviven) && labeled(c.cuidador_principal) && labeled(c.observaciones) &&
    text(x.ciudadano_2) && text(x.vinculo) && text(x.estado_relacion) && typeof x.conviven === "boolean" && typeof x.cuidador_principal === "boolean" && text(x.observaciones) &&
    Object.values(v.errors).every((e) => Array.isArray(e) && e.every(text)) &&
    Array.isArray(v.messages) && v.messages.every((m) => record(m) && text(m.message) && LEVELS.includes(m.level as string));
}

/** Replaceable in tests: the confirmed redirect and the history back are full-page navigations, like the native ones. */
export const ciudadanoFamiliarNavigation = { assign: (to: string) => window.location.assign(to), back: () => window.history.back() };

type Section = "familiar" | "relacion" | "notas";
const filled = (s: string) => s.trim().length > 0;

function sectionStates(id: string, v: Values): Record<Section, "complete" | "empty"> {
  const relacion = filled(v.vinculo) || filled(v.estado_relacion) || v.conviven || v.cuidador_principal;
  const state = (done: boolean) => (done ? "complete" : "empty");
  return { familiar: state(filled(id)), relacion: state(relacion), notas: state(filled(v.observaciones)) };
}

// The template script also knows an "Incompleta" badge, but its condition equals the "Completa" one: it never shows.
const BADGE = { complete: ["complete", "fa-check-circle", "Completa"], empty: ["empty", "fa-circle", "Sin completar"] } as const;

function SectionCard({ id, icon, title, subtitle, state, open, toggle, children }: {
  id: Section; icon: string; title: string; subtitle: string; state: keyof typeof BADGE; open: boolean; toggle: () => void; children: ReactNode;
}) {
  const [cls, glyph, label] = BADGE[state];
  return (
    <div className="section-card" data-section={id}>
      <div className={`section-header${open ? "" : " collapsed"}`} data-toggle-section={id} tabIndex={0} role="button" onClick={toggle}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } }}>
        <div className="section-header-left">
          <div className="section-icon"><i className={`fas ${icon}`} /></div>
          <div className="section-title-group"><h3 className="section-title">{title}</h3><p className="section-subtitle">{subtitle}</p></div>
        </div>
        <div className="section-status">
          <span className={`status-badge ${cls}`} id={`status-${id}`}><i className={`fas ${glyph}`} /> {label}</span>
          <div className="collapse-indicator"><i className="fas fa-chevron-down" /></div>
        </div>
      </div>
      <div className={`section-body collapse${open ? " show" : ""}`} id={`section-${id}`}>{children}</div>
    </div>
  );
}

const SUGGESTIONS = { position: "absolute", background: "white", border: "1px solid #ddd", borderRadius: 4, maxHeight: 200, overflowY: "auto", zIndex: 1000, minWidth: 300 } as const;
type Result = { id: number; text: string };

/** The template script: 4+ characters search `/api/ciudadanos/buscar/`, a click fills the text and the hidden id. */
function FamiliarSearch({ data, value, setValue, id, setId, error, exclude }: {
  data: FamiliarData; value: string; setValue: (v: string) => void; id: string; setId: (id: string) => void; error: string[]; exclude: number;
}) {
  const [results, setResults] = useState<Result[] | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const latest = useRef(0);
  useEffect(() => {
    const hide = (e: MouseEvent) => { if (e.target !== input.current && e.target !== box.current) setResults(null); };
    document.addEventListener("click", hide);
    return () => document.removeEventListener("click", hide);
  }, []);
  async function search(query: string) {
    const mine = ++latest.current;
    if (query.length < 4) { setResults(null); return; }
    try {
      const { data: body } = await webClient.get("ciudadanos/buscar/", { params: { q: query, exclude_id: exclude } });
      if (mine !== latest.current) return;
      if (record(body) && Array.isArray(body.results)) setResults(body.results.filter((r): r is Result => record(r) && Number.isSafeInteger(r.id) && text(r.text)));
    } catch { /* the native script has no error path either */ }
  }
  const campo = data.campos.ciudadano_2;
  return (
    <div className="form-group" style={{ position: "relative" }}>
      <label htmlFor="id_ciudadano_2">{campo.label}</label>
      <input type="text" name="ciudadano_2" className="form-control" placeholder={campo.placeholder} autoComplete="off" required id="id_ciudadano_2" value={value} ref={input}
        aria-invalid={error.length > 0 ? true : undefined} aria-describedby={error.length > 0 ? "id_ciudadano_2_error" : undefined}
        onChange={(e) => { setValue(e.target.value); void search(e.target.value.trim()); }} />
      <input type="hidden" id="id_ciudadano_2_id" name="ciudadano_2_id" value={id} readOnly />
      {error.length > 0 && <div className="text-danger small mt-1">{error.join(", ")}</div>}
      {results && (
        <div id="ciudadano-suggestions" ref={box} style={SUGGESTIONS}>
          {results.length === 0 ? <div style={{ padding: 10, color: "#999" }}>No se encontraron resultados</div> : results.map((r) => (
            <div key={r.id} style={{ padding: 10, cursor: "pointer", borderBottom: "1px solid #eee" }}
              onMouseOver={(e) => { e.currentTarget.style.backgroundColor = "#f0f0f0"; }} onMouseOut={(e) => { e.currentTarget.style.backgroundColor = "transparent"; }}
              onClick={() => { setValue(r.text); setId(String(r.id)); setResults(null); }}>{r.text}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function Select({ name, campo, value, set }: { name: string; campo: { label: string; options: Option[] }; value: string; set: (v: string) => void }) {
  return (
    <div id={`div_id_${name}`} className="mb-3">
      <label htmlFor={`id_${name}`} className="form-label">{campo.label}</label>
      <select name={name} className="form-select" id={`id_${name}`} value={value} onChange={(e) => set(e.target.value)}>
        {campo.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

export function FamiliarContent({ data: initial }: { data: FamiliarData }) {
  const [data, setData] = useState(initial);
  const [values, setValues] = useState(initial.values);
  const [familiarId, setFamiliarId] = useState("");
  const [open, setOpen] = useState<Record<Section, boolean>>({ familiar: true, relacion: true, notas: true });
  const [toasts, setToasts] = useState(initial.messages);
  const [pending, setPending] = useState(false);
  const busy = useRef(false);
  const set = <K extends keyof Values>(k: K, v: Values[K]) => setValues((cur) => ({ ...cur, [k]: v }));
  const states = sectionStates(familiarId, values);
  const completed = Object.values(states).filter((s) => s === "complete").length;
  const toggle = (s: Section) => setOpen((cur) => ({ ...cur, [s]: !cur[s] }));
  const { ciudadano, campos, errors } = data;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams({ ciudadano_2_id: familiarId, ciudadano_2: values.ciudadano_2, vinculo: values.vinculo, estado_relacion: values.estado_relacion, observaciones: values.observaciones });
    if (values.conviven) body.set("conviven", "on");
    if (values.cuidador_principal) body.set("cuidador_principal", "on");
    const outcome = await postForm(`web/ciudadanos/${ciudadano.id}/familiares/nuevo/`, body);
    if (outcome.kind === "redirect") { ciudadanoFamiliarNavigation.assign(outcome.url); return; }
    busy.current = false; setPending(false);
    if (outcome.kind === "invalid" && familiarValid(outcome.data)) {
      // The native page reloads with the bound form: the text input shows what was posted as `ciudadano_2`
      // (the id), the hidden id is empty again, every section is open and the view starts at the top.
      setData(outcome.data); setValues(outcome.data.values); setFamiliarId(""); setOpen({ familiar: true, relacion: true, notas: true });
      setToasts(outcome.data.messages); resetAfterRejectedPost();
      return;
    }
    setToasts([{ message: outcome.kind === "forbidden" && record(outcome.data) && text(outcome.data.detail) ? outcome.data.detail : UNCERTAIN, level: "error" }]);
  }

  return (
    <>
      <NativeToasts messages={toasts} />
      <link rel="stylesheet" href="/static/custom/css/comedorRelevamiento.css" />
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <div className="d-flex justify-content-between mb-3">
        <div><a href="#" data-history-back="true" className="btn btn-secondary" onClick={(e) => { e.preventDefault(); ciudadanoFamiliarNavigation.back(); }}>Cancelar</a></div>
      </div>
      <div className="row comedor-form">
        <div className="col-12 col-lg-10 mx-auto">
          <div className="mb-4">
            <h3 className="text-light mb-1">Agregar familiar para {ciudadano.texto}</h3>
            <p className="text-muted mb-0">Registrá el vínculo y los datos principales del grupo familiar.</p>
          </div>
          <form method="post" id="grupoFamiliarForm" className="w-100" noValidate onSubmit={submit}>
            <div className="progress-indicator">
              <div className="progress-header">
                <h4 className="progress-title"><i className="fas fa-users mr-2" />{" "}Progreso del formulario</h4>
                <span className="progress-stats"><span id="completedSections">{completed}</span>/3 secciones completadas</span>
              </div>
              <div className="progress-bar-container"><div className="progress-bar-fill" id="progressBarFill" style={{ width: `${Math.round((completed / 3) * 100)}%` }} /></div>
            </div>
            <SectionCard id="familiar" icon="fa-user-friends" title="Familiar" subtitle="Seleccioná la persona relacionada" state={states.familiar} open={open.familiar} toggle={() => toggle("familiar")}>
              <FamiliarSearch data={data} value={values.ciudadano_2} setValue={(v) => set("ciudadano_2", v)} id={familiarId} setId={setFamiliarId} error={errors.ciudadano_2 ?? []} exclude={ciudadano.id} />
            </SectionCard>
            <SectionCard id="relacion" icon="fa-heart" title="Relación" subtitle="Definí el vínculo y la convivencia" state={states.relacion} open={open.relacion} toggle={() => toggle("relacion")}>
              <div className="form-group row">
                <div className="col-md-6"><Select name="vinculo" campo={campos.vinculo} value={values.vinculo} set={(v) => set("vinculo", v)} /></div>
                <div className="col-md-6"><Select name="estado_relacion" campo={campos.estado_relacion} value={values.estado_relacion} set={(v) => set("estado_relacion", v)} /></div>
              </div>
              <div className="form-group row">
                <div className="col-md-6 d-flex align-items-center">
                  <div className="form-check form-switch">
                    <input type="checkbox" name="conviven" className="form-check-input" id="id_conviven" checked={values.conviven} onChange={(e) => set("conviven", e.target.checked)} />
                    <label className="form-check-label ms-2" htmlFor="id_conviven">{campos.conviven.label}</label>
                  </div>
                </div>
                <div className="col-md-6 d-flex align-items-center">
                  <div className="form-check form-switch">
                    <input type="checkbox" name="cuidador_principal" className="form-check-input" id="id_cuidador_principal" checked={values.cuidador_principal} onChange={(e) => set("cuidador_principal", e.target.checked)} />
                    <label className="form-check-label ms-2" htmlFor="id_cuidador_principal">{campos.cuidador_principal.label}</label>
                  </div>
                </div>
              </div>
            </SectionCard>
            <SectionCard id="notas" icon="fa-sticky-note" title="Notas adicionales" subtitle="Observaciones relevantes" state={states.notas} open={open.notas} toggle={() => toggle("notas")}>
              <div className="form-group">
                <div id="div_id_observaciones" className="mb-3">
                  <label htmlFor="id_observaciones" className="form-label">{campos.observaciones.label}</label>
                  <textarea name="observaciones" cols={40} rows={2} className="form-control textarea" id="id_observaciones" value={values.observaciones} onChange={(e) => set("observaciones", e.target.value)} />
                </div>
              </div>
            </SectionCard>
            <div className="sticky-actions">
              <div><a href={ciudadano.volver_url} className="btn btn-secondary"><i className="fas fa-arrow-left mr-1" /> Volver</a></div>
              <div>
                <button type="button" data-history-back="true" className="btn btn-secondary mr-2" onClick={() => ciudadanoFamiliarNavigation.back()}><i className="fas fa-times mr-1" /> Cancelar</button>
                {" "}<button type="submit" className="btn btn-success" disabled={pending}><i className="fas fa-save mr-1" /> Guardar familiar</button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

function FamiliarPage({ pk }: { pk: string }) {
  const [state] = useMainResource(`web/ciudadanos/${pk}/familiares/nuevo/`, familiarValid);
  return renderMain(state, "Cargando ciudadano…", (data) => ({ title: "Grupo familiar", heading: "Grupo familiar", breadcrumb: null, content: <FamiliarContent data={data} /> }));
}

const FAMILIAR = /^\/ciudadanos\/([0-9]+)\/familiares\/nuevo$/;

export const ciudadanoFamiliarRoute: RouteDefinition<{ pk: string }> = {
  name: "ciudadano-familiar-nuevo",
  match(pathname) {
    const found = FAMILIAR.exec(pathname);
    return found ? { pk: found[1] } : null;
  },
  render({ pk }) {
    return <FamiliarPage pk={pk} />;
  },
};
