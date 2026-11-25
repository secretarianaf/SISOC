/* eslint-disable react-refresh/only-export-components -- the unit surface is this route module; its screen and helpers live here with the route. */
import { Fragment, useEffect, useRef, useState, type FormEvent, type KeyboardEvent, type ReactNode } from "react";
import { leerCookie } from "@sisoc/api";
import InsumosAccessError from "../InsumosAccessError";
import { prerequisiteFromForbidden, type WebPrerequisite } from "../webAccess";
import { Casilla, Checks, Crispy, destinatarioValid, type Campo, type DestinatarioData } from "./cdiDestinatarioCampos";
import {
  aOpciones, calcularEdad, cargarLista, progress, SECCIONES, SIN_ALCANCE, VACIO, VACUNAS, type Estado, type GeoOption, type Multi, type Seccion, type Values,
} from "./cdiDestinatarioForm.behavior";
import { client, internal, navigation, record, renderCdi, text, useCdiPage } from "./cdiFrame";
import { handleInvalid, RenaperBloque, useRenaperBloque, type BloqueSpec } from "./cdiRenaperBloque";
import { resetAfterRejectedPost } from "./nativeParity";
import type { RouteDefinition } from "./types";

/**
 * CDI destinatario create and edit (`centrodeinfancia/destinatario_form.html`): the DNI search, the
 * progress bar, the collapsible section cards with the three RENAPER blocks, and the behaviour script
 * (`destinatarioForm.js`, `cdiSinCuil.js`, `cdiRenaperBloques.js`). The native views stay the authority
 * through `/api/web/cdi/centros/<pk>/nomina/crear/` and `.../<id>/editar/`: this page posts only the
 * fields the template draws, once, and a rejected save redraws the page with the server errors.
 */
const UNCERTAIN = "No se pudo confirmar el resultado. Verificá el estado antes de reintentar.";
const CUIT_DE: Record<string, string> = { sin_cuil_nino: "cuit_nino", responsable_legal_1_sin_cuil: "responsable_legal_1_cuit" };
const CUIT_INICIAL = Object.fromEntries(Object.entries(CUIT_DE).map(([casilla, cuit]) => [cuit, casilla]));
const NINO_SCOPE = ["apellido", "nombre", "fecha_nacimiento", "edad_calculada", "edad_unidad", "sexo", "tipo_documentacion", "dni", "cuit_nino", "sin_cuil_nino", "pais_nacimiento", "nacionalidad", "sala"];
const resp = (p: string) => ["tipo_documentacion", "dni", "apellido", "nombre", "fecha_nacimiento", "cuit", "sin_cuil", "sexo_registral", "nacionalidad", "relacion", "telefono", "pais_nacimiento", "nivel_educativo", "consentimiento"].map((n) => `${p}_${n}`);
const VACIO_SPEC = { bloque: "nino", url: "", modo: "manual", campos: [], tipo_field: "", tipos_con_dni: [], verificado: false, permite_cambiar: false, opcional: false, token: "" } as const;
const BADGE: Record<Estado, { icon: string; label: string }> = {
  complete: { icon: "fa-check-circle", label: "Completada" }, incomplete: { icon: "fa-exclamation-circle", label: "Incompleta" }, empty: { icon: "fa-circle", label: "Sin completar" },
};
const CARD = { background: "#2c3e50", border: "1px solid #374151" };

function Section({ id, icon, title, subtitle, estado, children }: { id: string; icon: string; title: string; subtitle: string; estado?: Estado; children: ReactNode }) {
  const [open, setOpen] = useState(true);
  const toggle = () => setOpen((current) => !current);
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } };
  return (
    <div className="section-card" data-section={id}>
      <div className={`section-header${open ? "" : " collapsed"}`} data-toggle-section={id} tabIndex={0} role="button" aria-expanded={open} onClick={toggle} onKeyDown={onKey}>
        <div className="section-header-left">
          <div className="section-icon"><i className={`fas ${icon}`} /></div>
          <div className="section-title-group">
            <h3 className="section-title">{title}</h3>
            <p className="section-subtitle">{subtitle}</p>
          </div>
        </div>
        <div className="section-status">
          {estado && <span className={`status-badge ${estado}`} id={`status-${id}`}><i className={`fas ${BADGE[estado].icon}`} /> {BADGE[estado].label}</span>}
          <div className="collapse-indicator"><i className="fas fa-chevron-down" /></div>
        </div>
      </div>
      <div className={`section-body collapse${open ? " show" : ""}`} id={`section-${id}`}>{children}</div>
    </div>
  );
}

function Search({ search, selected, isEdit }: { search: NonNullable<DestinatarioData["search"]>; selected: DestinatarioData["selected"]; isEdit: boolean }) {
  if (isEdit) return null;
  return (
    <div className="card mb-4" style={CARD}>
      <div className="card-body">
        <h5 className="mb-3" style={{ color: "#e5e7eb" }}><i className="fas fa-search me-2" style={{ color: "#f39c12" }} />Buscar niño/a por DNI</h5>
        <form method="get" className="row g-2 align-items-end">
          <div className="col-md-4">
            <label htmlFor="busqueda-dni" className="form-label">DNI</label>
            <input type="text" className="form-control" name="query" id="busqueda-dni" placeholder="Ingrese DNI (mín. 4 dígitos)" defaultValue={search.query} />
          </div>
          <div className="col-md-auto">
            <button className="btn btn-warning" type="submit"><i className="fas fa-search me-1" />Buscar</button>
          </div>
        </form>
        {search.ciudadanos.length > 0 && !selected && (
          <div className="mt-3 table-responsive">
            <table className="table table-dark table-hover table-sm mb-0">
              <thead><tr><th>Apellido</th><th>Nombre</th><th>DNI</th><th /></tr></thead>
              <tbody>
                {search.ciudadanos.map((c) => (
                  <tr key={c.id}>
                    <td>{c.apellido}</td><td>{c.nombre}</td><td>{c.documento}</td>
                    <td><a href={`?query=${search.query}&ciudadano_id=${c.id}`} className="btn btn-sm btn-success">Completar ficha</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {search.query && search.no_resultados && (search.renaper_precarga
          ? <div className="alert alert-success mt-2 mb-0"><i className="fas fa-id-card me-1" />Datos de identidad obtenidos de RENAPER. Completá el resto de la ficha para agregar al niño/a a la nómina.</div>
          : <div className="alert alert-info mt-2 mb-0">No se encontraron datos para el DNI buscado. Podés completar la ficha manualmente.</div>)}
      </div>
    </div>
  );
}

function edadDe(fecha: string, actual: Values): Values {
  const { edad, unidad } = calcularEdad(fecha);
  return { edad_calculada: edad, edad_unidad: unidad ?? actual.edad_unidad ?? "" };
}
const initialValues = (fields: Campo[]): Values => {
  const values = Object.fromEntries(fields.map((f) => [f.name, f.widget === "checkbox" ? (f.checked ? "on" : "") : f.value]));
  // `calcular(fechaNacInput.value)` runs once at load.
  return { ...values, ...edadDe(values.fecha_nacimiento ?? "", values) };
};
const initialMulti = (data: DestinatarioData): Multi => Object.fromEntries(Object.entries(data.multiples).map(([n, g]) => [n, g.options.filter((o) => o.checked).map((o) => o.value)]));

type Geo = { departamento: GeoOption[] | null; municipio: GeoOption[] | null; localidad: GeoOption[] | null; sinAlcance: boolean };

export function DestinatarioForm({ data, endpoint, onRejected }: { data: DestinatarioData; endpoint: string; onRejected: (next: DestinatarioData) => void }) {
  const [values, setValues] = useState<Values>(() => initialValues(data.fields));
  const [multi, setMulti] = useState<Multi>(() => initialMulti(data));
  const [geo, setGeo] = useState<Geo>({ departamento: null, municipio: null, localidad: null, sinAlcance: false });
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [forbidden, setForbidden] = useState<{ prerequisite: WebPrerequisite | null } | null>(null);
  const busy = useRef(false);
  const byName = new Map(data.fields.map((f) => [f.name, f]));
  const field = (name: string) => byName.get(name) as Campo;
  const [sinCuilInicial] = useState(() => new Set(Object.keys(CUIT_DE).filter((n) => byName.get(n)?.checked)));
  const geoUrls = data.urls;

  const set = (name: string, value: string) => setValues((prev) => {
    const next = { ...prev, [name]: value };
    // A CUIT loaded by hand or from RENAPER unchecks its "No posee CUIL".
    const casilla = Object.keys(CUIT_DE).find((c) => CUIT_DE[c] === name);
    if (casilla && value !== "") next[casilla] = "";
    // "No posee CUIL" empties its CUIT.
    if (CUIT_DE[name] && value === "on") next[CUIT_DE[name]] = "";
    // Age from the birth date on every change (the unit select follows).
    if (name === "fecha_nacimiento") Object.assign(next, edadDe(value, next));
    return next;
  });
  const io = { get: (name: string) => values[name] ?? "", set };

  const serverLocked = (campos: string[]) => campos.filter((n) => byName.get(n)?.renaper && byName.get(n)?.disabled);
  const spec = (cfg: DestinatarioData["renaper"]["responsable_legal_1"] | null, dni: string, scope: string[], textoAgregar?: string): BloqueSpec =>
    cfg ? { ...cfg, dni, scope, serverLocked: serverLocked(cfg.campos), textoAgregar } : { ...VACIO_SPEC, modo: "manual", campos: [], tipos_con_dni: [], dni, scope: [], serverLocked: [] };
  const nino = useRenaperBloque(spec(data.renaper.nino, "dni", NINO_SCOPE), io);
  const r1 = useRenaperBloque(spec(data.renaper.responsable_legal_1, "responsable_legal_1_dni", resp("responsable_legal_1")), io);
  const r2 = useRenaperBloque(spec(data.renaper.responsable_legal_2, "responsable_legal_2_dni", resp("responsable_legal_2").filter((n) => !n.endsWith("sin_cuil")), "Agregar responsable 2"), io);
  const blocks = [nino, r1, r2];
  const blockOf = (name: string) => blocks.find((b) => b.spec.scope.includes(name));
  const hid = (name: string) => blockOf(name)?.hidden(name) ?? false;

  // Geography: the lists the native script loads for a province already chosen.
  useEffect(() => {
    const provincia = values.provincia_domicilio;
    if (!provincia) return undefined;
    let alive = true;
    const inicial = { departamento: values.departamento, municipio: values.municipio_domicilio, localidad: values.localidad_domicilio };
    Promise.all([cargarLista(`${geoUrls.departamentos}?provincia_id=${provincia}`), cargarLista(`${geoUrls.municipios}?provincia_id=${provincia}`)])
      .then(async ([deps, muns]) => {
        const departamento = aOpciones(deps, VACIO.departamento);
        const municipio = aOpciones(muns, VACIO.municipio);
        const elegido = departamento.find((o) => o.value === inicial.departamento);
        let localidad: GeoOption[] | null = null;
        const muniOk = municipio.some((o) => o.value === inicial.municipio);
        if (inicial.municipio && muniOk) localidad = aOpciones(await cargarLista(`${geoUrls.localidades}?municipio_id=${inicial.municipio}`), VACIO.localidad);
        if (!alive) return;
        setGeo({ departamento, municipio, localidad, sinAlcance: muns.length === 0 });
        setValues((prev) => ({
          ...prev, departamento: elegido ? inicial.departamento : "", decil_ipi: elegido?.decil ?? "",
          municipio_domicilio: muniOk ? inicial.municipio : "",
          localidad_domicilio: localidad?.some((o) => o.value === inicial.localidad) ? inicial.localidad : "",
        }));
      })
      .catch(() => undefined);
    return () => { alive = false; };
    // Only at load: the change handlers below own every later reload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onProvincia(value: string) {
    setValues((prev) => ({ ...prev, provincia_domicilio: value, departamento: "", decil_ipi: "", municipio_domicilio: "", localidad_domicilio: "" }));
    setGeo({ departamento: aOpciones([], VACIO.departamento), municipio: aOpciones([], VACIO.municipio), localidad: aOpciones([], VACIO.localidad), sinAlcance: false });
    if (!value) return;
    try {
      const deps = await cargarLista(`${geoUrls.departamentos}?provincia_id=${value}`);
      setGeo((g) => ({ ...g, departamento: aOpciones(deps, VACIO.departamento) }));
      const muns = await cargarLista(`${geoUrls.municipios}?provincia_id=${value}`);
      setGeo((g) => ({ ...g, municipio: aOpciones(muns, VACIO.municipio), sinAlcance: muns.length === 0 }));
    } catch { /* the native script only logs it */ }
  }
  async function onMunicipio(value: string) {
    setValues((prev) => ({ ...prev, municipio_domicilio: value, localidad_domicilio: "" }));
    setGeo((g) => ({ ...g, localidad: aOpciones([], VACIO.localidad) }));
    if (!value) return;
    try {
      const locs = await cargarLista(`${geoUrls.localidades}?municipio_id=${value}`);
      setGeo((g) => ({ ...g, localidad: aOpciones(locs, VACIO.localidad) }));
    } catch { /* the native script only logs it */ }
  }
  const onDepartamento = (value: string) => setValues((prev) => ({ ...prev, departamento: value, decil_ipi: geo.departamento?.find((o) => o.value === value)?.decil ?? "" }));

  const campo = (name: string): Campo => {
    const base = field(name);
    const lista = name === "departamento" ? geo.departamento : name === "municipio_domicilio" ? geo.municipio : name === "localidad_domicilio" ? geo.localidad : null;
    return lista ? { ...base, choices: lista.map(({ value, label }) => ({ value, label })) } : base;
  };
  const handlers: Record<string, (v: string) => void> = { provincia_domicilio: (v) => void onProvincia(v), municipio_domicilio: (v) => void onMunicipio(v), departamento: onDepartamento };

  /** `{{ form.<name>|as_crispy_field }}`; the RENAPER block of its section governs lock and visibility. */
  function f(name: string, opts: { dni?: boolean; small?: boolean } = {}) {
    const c = campo(name);
    if (c.widget === "checkbox") return <Casilla field={c} checked={values[name] === "on"} onChange={(on) => set(name, on ? "on" : "")} />;
    const block = blockOf(name);
    const casilla = CUIT_INICIAL[name];
    const marcada = casilla ? values[casilla] === "on" : false;
    const tipo = block && block.spec.tipo_field === name;
    const change = (v: string) => { (handlers[name] ?? ((x: string) => set(name, x)))(v); if (tipo) block.onTipo(v); };
    const extra = name === "municipio_domicilio" && geo.sinAlcance
      ? <div id="id_municipio_domicilio-hint" className="form-text text-warning small mt-1">{SIN_ALCANCE}</div> : null;
    return (
      <Crispy field={c} value={values[name] ?? ""} onChange={change} block={block} dni={opts.dni} small={opts.small} after={extra}
        readOnly={casilla && marcada ? true : undefined}
        required={casilla ? (c.required || sinCuilInicial.has(casilla)) && !marcada : undefined} />
    );
  }

  const checks = (name: string) => (
    <Checks name={name} grupo={data.multiples[name]} selected={multi[name] ?? []}
      onToggle={(v) => setMulti((prev) => ({ ...prev, [name]: (prev[name] ?? []).includes(v) ? (prev[name] ?? []).filter((x) => x !== v) : [...(prev[name] ?? []), v] }))} />
  );
  const col = (cls: string, names: string | string[]) => {
    const list = Array.isArray(names) ? names : [names];
    return (
      <div className={cls} hidden={hid(list[0]) || undefined}>
        {list.map((n) => <Fragment key={n}>{f(n)}</Fragment>)}
      </div>
    );
  };

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    busy.current = true; setPending(true);
    const body = new URLSearchParams({ csrfmiddlewaretoken: leerCookie("csrftoken") ?? "" });
    if (data.selected) body.set("ciudadano_id", String(data.selected.id));
    if (data.renaper_prefill_token) body.set("renaper_prefill_token", data.renaper_prefill_token);
    data.fields.forEach((fl) => {
      if (fl.disabled && !fl.renaper) return;
      if (blockOf(fl.name)?.lock(fl.name) === "server") return;
      if (fl.widget === "checkbox") { if (values[fl.name] === "on") body.append(fl.name, "on"); return; }
      body.append(fl.name, values[fl.name] ?? "");
    });
    Object.entries(multi).forEach(([n, vs]) => vs.forEach((v) => body.append(n, v)));
    [["nino", nino, data.renaper.nino], ["responsable_legal_1", r1, data.renaper.responsable_legal_1], ["responsable_legal_2", r2, data.renaper.responsable_legal_2]].forEach(([b, api, cfg]) => {
      if (cfg) body.set(`renaper_token_${b as string}`, (api as typeof nino).token);
    });
    try {
      const { data: reply, status } = await client.post(endpoint, body, { validateStatus: (s: number) => (s >= 200 && s < 300) || s === 400 || s === 403 || s === 404 });
      if (status === 403) { setForbidden({ prerequisite: prerequisiteFromForbidden(reply) }); return; }
      if (status === 400 && destinatarioValid(reply)) { onRejected(reply); return; }
      if (status >= 200 && status < 300 && record(reply) && reply.ok === true && text(reply.redirect) && internal(reply.redirect)) { navigation.assign(reply.redirect); return; }
      setUncertain(true);
    } catch {
      setUncertain(true);
    } finally {
      busy.current = false; setPending(false);
    }
  }

  if (forbidden) return <InsumosAccessError prerequisite={forbidden.prerequisite} />;
  const { estados, completadas } = progress(values, multi);
  const estado = (id: Seccion) => estados[id];
  const info = (name: string) => ({ label: field(name).label, type: field(name).widget, choices: field(name).choices });
  const { centro } = data;
  const titulo = data.is_edit ? "Editar destinatario" : "Agregar destinatario";
  const dash = { color: "#9ca3af" };
  const val = { color: "#e5e7eb" };
  const show = data.is_edit || data.mostrar_formulario;
  const grupoIndigena = (multi.grupo_pertenencia ?? []).includes("indigena");
  return (
    <>
      <link rel="stylesheet" href="/static/custom/css/comedorFormModerno.css" />
      <div className="container-fluid">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item"><a href={centro.url}>{centro.nombre} — Nómina</a></li>
              <li className="breadcrumb-item active">{titulo}</li>
            </ol>
          </nav>
        </div>
        {data.search && <Search search={data.search} selected={data.selected} isEdit={data.is_edit} />}
        {show && (
          <>
            {data.selected && (
              <div className="alert alert-light border mb-3">
                Completando ficha para:{" "}
                <strong>{data.selected.apellido}, {data.selected.nombre}</strong>{" "}
                (DNI {data.selected.documento || "-"}).
              </div>
            )}
            <form method="post" id="destinatarioForm" onSubmit={(e) => void submit(e)} onInvalidCapture={(e) => handleInvalid(e, blocks)}>
              {data.non_field_errors.length > 0 && <div className="alert alert-danger mb-3"><ul className="errorlist nonfield">{data.non_field_errors.map((m, i) => <li key={i}>{m}</li>)}</ul></div>}
              <div className="progress-indicator">
                <div className="progress-header">
                  <h4 className="progress-title"><i className="fas fa-child me-2" />Destinatario CDI</h4>
                  <div className="progress-stats"><span id="completedSections">{completadas}</span> / {SECCIONES.length} secciones completadas</div>
                </div>
                <div className="progress-bar-container"><div className="progress-bar-fill" id="progressBarFill" style={{ width: `${(completadas / SECCIONES.length) * 100}%` }} /></div>
              </div>

              <Section id="institucion" icon="fa-building" title="Institución y Espacio Temporal" subtitle="Datos del CDI donde se registra la ficha">
                <div className="form-group row">
                  <div className="col-md-4"><p className="small mb-1" style={dash}>Nombre de institución</p><p className="mb-2" style={val}>{centro.nombre_visible}</p></div>
                  <div className="col-md-2"><p className="small mb-1" style={dash}>Código CDI</p><p className="mb-2" style={val}>{centro.codigo_cdi}</p></div>
                  <div className="col-md-3"><p className="small mb-1" style={dash}>Jurisdicción</p><p className="mb-2" style={val}>{centro.provincia}</p></div>
                  <div className="col-md-3"><p className="small mb-1" style={dash}>Departamento</p><p className="mb-2" style={val}>{centro.departamento}</p></div>
                </div>
                <div className="form-group row">
                  <div className="col-md-3"><p className="small mb-1" style={dash}>Municipio</p><p className="mb-2" style={val}>{centro.municipio}</p></div>
                  <div className="col-md-3"><p className="small mb-1" style={dash}>Localidad</p><p className="mb-2" style={val}>{centro.localidad}</p></div>
                </div>
              </Section>

              <Section id="registro" icon="fa-clipboard-list" title="Registro" subtitle="Tipo de registro, fecha y referente del CDI" estado={estado("registro")}>
                <div className="form-group row">
                  {col("col-md-3", "estado")}{col("col-md-3", "tipo_registro")}{col("col-md-3", "fecha_registro")}{col("col-md-5", "trabajador_registra")}
                </div>
              </Section>

              <Section id="nino" icon="fa-baby" title="Datos del niño/a" subtitle="Identidad, documentación y sala" estado={estado("nino")}>
                {data.renaper.nino && <RenaperBloque api={nino} info={info} values={values} />}
                <div className="form-group row">
                  {col("col-md-3", "apellido")}{col("col-md-3", "nombre")}{col("col-md-3", "fecha_nacimiento")}{col("col-md-2", "edad_calculada")}{col("col-md-2", "edad_unidad")}
                </div>
                <div className="form-group row">
                  {col("col-md-3", "sexo")}{col("col-md-3", "tipo_documentacion")}
                  <div className={"col-md-3"} hidden={hid("dni") || undefined}>{f("dni", { dni: true })}</div>
                  {col("col-md-3", ["cuit_nino", "sin_cuil_nino"])}
                </div>
                <div className="form-group row">{col("col-md-3", "pais_nacimiento")}{col("col-md-3", "nacionalidad")}{col("col-md-3", "sala")}</div>
              </Section>

              {([["responsable1", "responsable_legal_1", r1, "fa-user-shield", "Responsable 1", "Progenitor/a, tutor/a, curador/a o referente afectivo"],
                ["responsable2", "responsable_legal_2", r2, "fa-user-friends", "Responsable 2", "Opcional — obligatorio solo si se completa algún dato del bloque"]] as const).map(([id, p, api, icon, title, sub]) => (
                <Section key={id} id={id} icon={icon} title={title} subtitle={sub} estado={estado(id)}>
                  <div className="form-group row">
                    {col("col-md-3", `${p}_tipo_documentacion`)}
                    <div className="col-md-3" hidden={hid(`${p}_dni`) || undefined}>{f(`${p}_dni`, { dni: true })}</div>
                  </div>
                  <RenaperBloque api={api} info={info} values={values} />
                  <div className="form-group row">
                    {col("col-md-3", `${p}_apellido`)}{col("col-md-3", `${p}_nombre`)}{col("col-md-3", `${p}_fecha_nacimiento`)}
                    {col("col-md-3", id === "responsable1" ? [`${p}_cuit`, `${p}_sin_cuil`] : `${p}_cuit`)}
                  </div>
                  <div className="form-group row">{col("col-md-3", `${p}_sexo_registral`)}{col("col-md-3", `${p}_nacionalidad`)}</div>
                  <div className="form-group row">
                    {col("col-md-3", `${p}_relacion`)}{col("col-md-3", `${p}_telefono`)}{col("col-md-3", `${p}_pais_nacimiento`)}{col("col-md-3", `${p}_nivel_educativo`)}
                  </div>
                  <div className="form-group row">{col("col-md-3", `${p}_consentimiento`)}</div>
                </Section>
              ))}

              <Section id="domicilio" icon="fa-home" title="Domicilio principal" subtitle="Donde vive la mayor parte del tiempo" estado={estado("domicilio")}>
                <div className="form-group row">
                  {col("col-md-4", "calle_domicilio")}{col("col-md-2", "altura_domicilio")}{col("col-md-2", "piso_domicilio")}{col("col-md-2", "departamento_domicilio")}{col("col-md-3", "tipo_barrio")}
                </div>
                <div className="form-group row">{col("col-md-3", "provincia_domicilio")}{col("col-md-3", "departamento")}{col("col-md-2", "decil_ipi")}</div>
                <div className="form-group row">{col("col-md-3", "municipio_domicilio")}{col("col-md-3", "localidad_domicilio")}{col("col-md-3", "convivientes")}</div>
              </Section>

              <Section id="cultura" icon="fa-globe-americas" title="Cultura e Identidad" subtitle="Grupos de pertenencia y lenguajes del niño/a" estado={estado("cultura")}>
                <div className="form-group row">
                  <div className="col-md-6">{checks("grupo_pertenencia")}</div>
                  <div className={`col-md-6${grupoIndigena ? "" : " d-none"}`} id="row-pueblo-originario">{f("pueblo_originario_cual")}</div>
                </div>
                <div className="form-group row"><div className="col-md-6">{checks("lenguajes")}</div><div className="col-md-3">{f("necesito_interprete")}</div></div>
              </Section>

              <Section id="discapacidad" icon="fa-wheelchair" title="Discapacidad" subtitle="Tipo de discapacidad, apoyos y CUD" estado={estado("discapacidad")}>
                <div className="form-group row"><div className="col-md-4">{f("tiene_discapacidad")}</div></div>
                <div id="bloque-discapacidad" className={values.tiene_discapacidad === "si" ? undefined : "d-none"}>
                  <div className="form-group row"><div className="col-md-6">{checks("tipo_discapacidad")}</div></div>
                  <div className="form-group row">
                    <div className="col-md-3">{f("posee_cud")}</div>
                    <div className={`col-md-3${values.posee_cud === "true" ? "" : " d-none"}`} id="row-numero-cud">{f("numero_cud")}</div>
                  </div>
                </div>
                <div className="form-group row"><div className="col-md-4">{f("recibe_apoyo_desarrollo")}</div></div>
              </Section>

              <Section id="salud" icon="fa-heartbeat" title="Salud y Antropometría" subtitle="Cobertura, controles y medidas" estado={estado("salud")}>
                <div className="form-group row">
                  <div className="col-md-3">{f("cobertura_salud")}</div><div className="col-md-3">{f("controles_sanitarios_ultimo_anio")}</div><div className="col-md-3">{f("calendario_vacunacion_al_dia")}</div>
                </div>
                <div className="form-group row">
                  <div className="col-md-3">{f("talla")}</div><div className="col-md-3">{f("peso")}</div><div className="col-md-3">{f("longitud_acostado")}</div><div className="col-md-3">{f("perimetro_cefalico")}</div>
                </div>
              </Section>

              <Section id="nutricion" icon="fa-apple-alt" title="Nutrición y Asistencia ANSES" subtitle="Lactancia, diagnósticos, alergias y asignaciones" estado={estado("nutricion")}>
                <div className="form-group row"><div className="col-md-3">{f("lactancia")}</div></div>
                <div className="form-group row"><div className="col-md-6">{checks("alergias_alimentarias")}</div></div>
                <hr style={{ borderColor: "#374151" }} />
                <p className="small mb-2" style={dash}>Asistencia ANSES (hogares con embarazadas y niños hasta 48 meses)</p>
                <div className="form-group row">
                  <div className="col-md-3">{f("anses_auh")}</div><div className="col-md-3">{f("anses_aue")}</div><div className="col-md-3">{f("anses_acsi")}</div><div className="col-md-3">{f("anses_acn")}</div>
                </div>
              </Section>

              <Section id="vacunacion" icon="fa-syringe" title="Vacunación NOMIVAC" subtitle="Plan de vacunación obligatorio" estado={estado("vacunacion")}>
                <div className="table-responsive">
                  <table className="table table-sm table-dark" style={{ fontSize: "0.875rem" }}>
                    <thead><tr><th style={{ width: "35%" }}>Vacuna</th><th>Dosis recibidas</th><th>Fecha de última dosis</th></tr></thead>
                    <tbody>
                      {VACUNAS.map((codigo) => (
                        <tr key={codigo}>
                          <td>{VACUNA_NOMBRE[codigo]}</td>
                          <td><Raw name={`vacuna_${codigo}_dosis`} campo={campo(`vacuna_${codigo}_dosis`)} value={values[`vacuna_${codigo}_dosis`] ?? ""} onChange={(v) => set(`vacuna_${codigo}_dosis`, v)} /></td>
                          <td><Raw name={`vacuna_${codigo}_fecha`} campo={campo(`vacuna_${codigo}_fecha`)} value={values[`vacuna_${codigo}_fecha`] ?? ""} onChange={(v) => set(`vacuna_${codigo}_fecha`, v)} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>

              <Section id="observaciones" icon="fa-comment-alt" title="Observaciones" subtitle="Información adicional relevante">
                <div className="form-group row"><div className="col-md-12">{f("observaciones")}</div></div>
              </Section>

              <div className="d-flex justify-content-between mt-4 mb-5">
                <a href={data.urls.cancelar} className="btn btn-secondary">Cancelar</a>
                <button type="submit" className="btn btn-success btn-lg" disabled={pending || uncertain}>
                  <i className="fas fa-save me-2" />{" "}{data.is_edit ? "Guardar cambios" : "Agregar a nómina"}
                </button>
              </div>
              {uncertain && <p role="alert" className="mb-0">{UNCERTAIN}</p>}
            </form>
          </>
        )}
      </div>
    </>
  );
}

const VACUNA_NOMBRE: Record<string, string> = {
  bcg: "BCG", neumococo: "Neumococo Conjugada", quintuple: "Quíntuple o Pentavalente", polio: "Polio (IPV o SALK)", rotavirus: "Rotavirus",
  meningococo: "Meningococo ACYW", antigripal: "Antigripal", hepatitis_a: "Hepatitis A", triple_viral: "Triple Viral", varicela: "Varicela",
  triple_bacteriana_celular: "Triple Bacteriana Celular", triple_bacteriana_acelular: "Triple Bacteriana Acelular",
  sincicial_respiratorio: "Virus Sincicial Respiratorio", fiebre_amarilla: "Fiebre Amarilla",
};

/** `{{ form.<name> }}`: the bare widget of the vaccine table (no label, no feedback). */
function Raw({ name, campo, value, onChange }: { name: string; campo: Campo; value: string; onChange: (v: string) => void }) {
  const id = `id_${name}`;
  const err = campo.errors.length > 0 ? { "aria-invalid": "true" as const, "aria-describedby": `${id}_error` } : {};
  if (campo.widget === "select") {
    return (
      <select name={name} id={id} className="form-select form-select-sm" value={value} {...err} onChange={(e) => onChange(e.target.value)}>
        {(campo.choices ?? []).map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
      </select>
    );
  }
  return <input type="date" name={name} id={id} className="form-control form-control-sm" value={value} {...err} onChange={(e) => onChange(e.target.value)} />;
}

const OWN = /^\/centrodeinfancia\/([1-9]\d*)\/nomina\/(?:crear|([1-9]\d*)\/editar)\/$/;

function DestinatarioPage({ centro, id }: { centro: string; id?: string }) {
  const base = `web/cdi/centros/${centro}/nomina/`;
  const endpoint = `${id ? `${base}${id}/editar/` : `${base}crear/`}${id ? "" : window.location.search}`;
  const [state, setState] = useCdiPage(endpoint, destinatarioValid);
  return renderCdi(state, (data) => {
    const titulo = data.is_edit ? "Editar destinatario" : "Agregar destinatario";
    return {
      title: titulo, heading: titulo, bodyToasts: true,
      content: (
        <DestinatarioForm key={data.seq ?? 0} data={data} endpoint={endpoint}
            onRejected={(next) => { if (state.status === "ready") setState({ ...state, data: { ...next, seq: (data.seq ?? 0) + 1 } }); resetAfterRejectedPost(); }} />
      ),
    };
  });
}

// Native URLs of the destinatario create and edit (same trailing slash).
export const cdiDestinatarioFormRoute: RouteDefinition<{ centro: string; id?: string }> = {
  name: "cdi-destinatario-form",
  match: (pathname) => {
    const own = OWN.exec(pathname);
    return own ? { centro: own[1], id: own[2] } : null;
  },
  render: ({ centro, id }) => <DestinatarioPage centro={centro} id={id} />,
};
