import { useState, type CSSProperties, type ReactNode } from "react";
import { Control, list, type Api, type Choice, type Section } from "./usuariosControls";

/**
 * The Comedores cards of `user/user_form.html` and the visibility rules of
 * `user_mobile_access.js` plus the inline scope script: master switches, coordinator scope,
 * permission checkboxes, and the organization / space selector (tabs, search, tables).
 * The server owns every option, default and error; this only repeats what the native scripts
 * do in the browser.
 */
export type Operator = { created_by: string; accesses: { space: string; created_by: string }[]; permission_labels: string[] };
export type CreatedUser = { username: string; email: string; active: boolean; spaces: string[]; permission_labels: string[] };

const hide = (hidden: boolean): CSSProperties | undefined => (hidden ? { display: "none" } : undefined);
const dash = (items: string[], render: (item: string, i: number) => ReactNode) => (items.length ? items.map(render) : "-");

export function OperatorContext({ operator }: { operator: Operator }) {
  return (
    <>
      <div className="alert alert-info mb-3" role="alert">
        <strong>Subusuario mobile.</strong>{" "}
        Este usuario fue creado desde SISOC - Mobile{operator.created_by ? ` por ${operator.created_by}` : ""}
        {" "}. El acceso y sus permisos se administran desde la app mobile por el usuario principal que lo creo.
      </div>
      <div className="table-responsive mb-3">
        <table className="table table-sm table-hover align-middle mb-0">
          <thead><tr><th>Espacio</th><th>Creado por</th><th>Permisos mobile</th></tr></thead>
          <tbody>
            {operator.accesses.map((access, i) => (
              <tr key={i}>
                <td>{access.space}</td>
                <td>{access.created_by || "-"}</td>
                <td>{dash(operator.permission_labels, (label, j) => <div key={j}>{label}</div>)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function CreatedUsersCard({ users }: { users: CreatedUser[] }) {
  return (
    <div className="card card-custom mb-3 shadow-sm" id="mobile-created-users-card">
      <div className="card-header card-header-custom"><h5 className="mb-0"><i className="fas fa-users mr-3" />Usuarios mobile creados por este usuario</h5></div>
      <div className="card-body">
        <div className="table-responsive">
          <table className="table table-sm table-hover align-middle mb-0">
            <thead><tr><th>Usuario</th><th>Email</th><th>Estado</th><th>Espacios</th><th>Permisos</th></tr></thead>
            <tbody>
              {users.map((item, i) => (
                <tr key={i}>
                  <td>{item.username}</td>
                  <td>{item.email || "-"}</td>
                  <td>{item.active ? <span className="badge badge-success">Activo</span> : <span className="badge badge-secondary">Inactivo</span>}</td>
                  <td>{dash(item.spaces, (name, j) => <div key={j}>{name}</div>)}</td>
                  <td>{dash(item.permission_labels, (label, j) => <div key={j}>{label}</div>)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export function TerritorialComedorBody({ section, api }: { section: Section; api: Api }) {
  const field = (name: string) => <Control spec={section.fields.find((f) => f.name === name)!} api={api} />;
  return (
    <>
      <div id="territorial-comedor-toggle-wrapper">{field("es_territorial_comedor")}</div>
      <div id="territorial-comedor-provincias-wrapper" style={hide(api.values.es_territorial_comedor !== true)}>{field("provincias_territorial")}</div>
    </>
  );
}

export function TeamsBody({ section, api }: { section: Section; api: Api }) {
  return <>{section.fields.map((f) => <Control key={f.name} spec={f} api={api} />)}</>;
}

const norm = (v: string) => v.trim().toLowerCase();

export function MobileBody({ section, api, operator }: { section: Section; api: Api; operator: Operator | null }) {
  const { values, set, busy } = api;
  const [tab, setTab] = useState<"organizaciones" | "espacios">(() => (list(values.organizaciones_pwa).length === 0 && list(values.comedores_pwa).length > 0 ? "espacios" : "organizaciones"));
  const [orgSearch, setOrgSearch] = useState("");
  const [orgSpaceSearch, setOrgSpaceSearch] = useState("");
  const [spaceSearch, setSpaceSearch] = useState("");
  if (operator) return <OperatorContext operator={operator} />;
  const by = (name: string) => section.fields.find((f) => f.name === name)!;
  const field = (name: string) => <Control spec={by(name)} api={api} />;
  const rep = values.es_representante_pwa === true;
  const coordinator = values.es_coordinador_equipo_tecnico_pwa === true;
  const readOnly = rep && coordinator;
  const isPwaUser = rep && !coordinator;
  const orgs = by("organizaciones_pwa").choices ?? [];
  const spaces: Choice[] = by("comedores_pwa").choices ?? [];
  const selectedOrgs = list(values.organizaciones_pwa);
  const selectedSpaces = list(values.comedores_pwa);
  const hasOrgs = selectedOrgs.length > 0;
  const orgSpaces = spaces.filter((c) => selectedOrgs.includes(c.organizacion_id ?? ""));
  const extraSpaces = spaces.filter((c) => !selectedOrgs.includes(c.organizacion_id ?? ""));

  function toggleOrg(id: string, checked: boolean) {
    const next = checked ? [...selectedOrgs, id] : selectedOrgs.filter((v) => v !== id);
    const own = spaces.filter((c) => (c.organizacion_id ?? "") === id).map((c) => c.value);
    // Adding an organization selects its spaces; removing it clears them (the native sync).
    set("organizaciones_pwa", next);
    set("comedores_pwa", checked ? [...selectedSpaces, ...own.filter((v) => !selectedSpaces.includes(v))] : selectedSpaces.filter((v) => !own.includes(v)));
  }
  function toggleSpace(id: string, checked: boolean) {
    set("comedores_pwa", checked ? [...selectedSpaces, id] : selectedSpaces.filter((v) => v !== id));
  }
  const visibleOrgs = orgs.filter((o) => !norm(orgSearch) || norm(o.label).includes(norm(orgSearch)));
  const matches = (c: Choice, term: string) => !norm(term) || norm(c.label).includes(norm(term)) || norm(c.organizacion_nombre ?? "").includes(norm(term));
  const visibleOrgSpaces = orgSpaces.filter((c) => matches(c, orgSpaceSearch));
  const visibleExtra = extraSpaces.filter((c) => matches(c, spaceSearch));
  const spaceRows = (rows: Choice[], prefix: string) => rows.map((c) => (
    <tr key={c.value}>
      <td className="mobile-selector-check-column">
        <div className="form-check mb-0">
          <input type="checkbox" className="form-check-input mobile-comedor-check" id={`${prefix}-comedor-${c.value}`} value={c.value} checked={selectedSpaces.includes(c.value)} disabled={busy} onChange={(e) => toggleSpace(c.value, e.target.checked)} />
        </div>
      </td>
      <td><label className="mb-0 w-100" htmlFor={`${prefix}-comedor-${c.value}`}>{c.label}</label></td>
      <td>{c.organizacion_nombre ?? ""}</td>
    </tr>
  ));
  const head = (first: string) => <thead><tr><th className={first === "org" ? "mobile-org-check-column" : "mobile-selector-check-column"} scope="col">Seleccionar</th><th scope="col">{first === "org" ? "Organización" : "Espacio"}</th>{first !== "org" && <th scope="col">Organización</th>}</tr></thead>;

  return (
    <>
      <div id="mobile-toggle-wrapper">{field("es_representante_pwa")}</div>
      <div id="mobile-coordinator-toggle-wrapper" style={hide(!rep)}>{field("es_coordinador_equipo_tecnico_pwa")}</div>
      <div id="mobile-coordinator-scope-wrapper" style={hide(!readOnly)}>{field("duplas_coordinador_pwa")}{field("comedores_adicionales_coordinador_pwa")}</div>
      <div id="mobile-rendicion-permission-wrapper" style={hide(!(rep && !readOnly))}>{field("puede_gestionar_rendiciones_mobile")}</div>
      <div id="mobile-pwa-permissions-wrapper" style={hide(!(rep && !readOnly))}>
        {field("puede_gestionar_colaboradores_pwa")}{field("puede_gestionar_usuarios_pwa")}{field("puede_gestionar_nomina_pwa")}{field("puede_gestionar_prestaciones_mensuales_pwa")}
      </div>
      <div id="mobile-association-type-wrapper" style={{ display: "none" }}>{field("tipo_asociacion_pwa")}</div>
      <div id="mobile-association-choice-wrapper" className="mb-3" style={hide(!isPwaUser)}>
        <div className="mobile-selector-intro">
          <div>
            <h6 className="mb-1">Configuración de alcance mobile</h6>
            <p className="mb-0">Podés seleccionar una o más organizaciones, elegir todos o algunos de sus espacios y además sumar espacios por fuera de esas organizaciones.</p>
          </div>
        </div>
        <div id="mobile-tabs" className="mobile-tabs" role="tablist" aria-label="Configuración de alcance">
          <button type="button" className={`mobile-tab-button${tab === "organizaciones" ? " is-active" : ""}`} role="tab" aria-selected={tab === "organizaciones"} onClick={() => setTab("organizaciones")}>Organizaciones</button>
          <button type="button" className={`mobile-tab-button${tab === "espacios" ? " is-active" : ""}`} role="tab" aria-selected={tab === "espacios"} onClick={() => setTab("espacios")}>Espacios</button>
        </div>
      </div>
      <div id="mobile-organizaciones-wrapper" style={hide(!isPwaUser || !(tab === "organizaciones" || hasOrgs))}>
        <div className="d-none">{field("organizaciones_pwa")}</div>
        <div id="mobile-organizaciones-table-panel" className="mobile-organizaciones-table-panel">
          <div className="mobile-selector-panel__header"><div><h6 className="mb-1">Organizaciones habilitadas</h6><p className="mb-0">Seleccioná una o más organizaciones para construir el alcance.</p></div></div>
          <label className="form-label" htmlFor="mobile-organizaciones-search">Buscar organizaciones</label>
          <input type="text" id="mobile-organizaciones-search" className="form-control mobile-selector-search mb-3" placeholder="Escriba para filtrar organizaciones" value={orgSearch} onChange={(e) => setOrgSearch(e.target.value)} />
          <div className="table-responsive mobile-organizaciones-table-scroll">
            <table className="table table-sm table-hover align-middle mb-0">
              {head("org")}
              <tbody id="mobile-organizaciones-table-body">
                {visibleOrgs.map((o) => (
                  <tr key={o.value}>
                    <td className="mobile-org-check-column"><div className="form-check mb-0"><input type="checkbox" className="form-check-input mobile-organizacion-check" id={`mobile-organizacion-${o.value}`} value={o.value} checked={selectedOrgs.includes(o.value)} disabled={busy} onChange={(e) => toggleOrg(o.value, e.target.checked)} /></div></td>
                    <td><label className="mb-0 w-100" htmlFor={`mobile-organizacion-${o.value}`}>{o.label}</label></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p id="mobile-organizaciones-empty-state" className="text-muted small mb-0 mt-2" style={hide(visibleOrgs.length !== 0)}>No hay organizaciones que coincidan con la búsqueda.</p>
        </div>
        <div id="mobile-comedores-organizacion-panel" className="mobile-selector-table-panel mt-3">
          <div className="mobile-selector-panel__header"><div><h6 className="mb-1">Espacios de las organizaciones seleccionadas</h6><p className="mb-0">Al seleccionar una organización se marcan sus espacios y aquí podés deseleccionar los que no correspondan.</p></div></div>
          <label className="form-label" htmlFor="mobile-comedores-organizacion-search">Buscar espacios de organizaciones</label>
          <input type="text" id="mobile-comedores-organizacion-search" className="form-control mobile-selector-search mb-3" placeholder="Escriba para filtrar espacios de organizaciones" value={orgSpaceSearch} onChange={(e) => setOrgSpaceSearch(e.target.value)} />
          <div className="table-responsive mobile-selector-table-scroll">
            <table className="table table-sm table-hover align-middle mb-0">{head("space")}<tbody id="mobile-comedores-organizacion-table-body">{spaceRows(visibleOrgSpaces, "mobile-comedores-organizacion-table-body")}</tbody></table>
          </div>
          <p id="mobile-comedores-organizacion-hint" className="text-muted small mb-0 mt-2" style={hide(orgSpaces.length !== 0)}>Seleccioná al menos una organización para ver sus espacios.</p>
          <p id="mobile-comedores-organizacion-empty-state" className="text-muted small mb-0 mt-2" style={hide(!(orgSpaces.length > 0 && visibleOrgSpaces.length === 0))}>No hay espacios de organizaciones que coincidan con la búsqueda.</p>
        </div>
      </div>
      <div id="mobile-comedores-wrapper" style={hide(!isPwaUser || tab !== "espacios")}>
        <div className="d-none">{field("comedores_pwa")}</div>
        <div id="mobile-comedores-table-panel" className="mobile-selector-table-panel">
          <div className="mobile-selector-panel__header"><div><h6 className="mb-1">Espacios</h6><p className="mb-0">Sumá espacios por fuera de las organizaciones seleccionadas. Los espacios ya mostrados en la pestaña de organizaciones no se repiten acá.</p></div></div>
          <label className="form-label" htmlFor="mobile-comedores-search">Buscar espacios</label>
          <input type="text" id="mobile-comedores-search" className="form-control mobile-selector-search mb-3" placeholder="Escriba para filtrar espacios" value={spaceSearch} onChange={(e) => setSpaceSearch(e.target.value)} />
          <div className="table-responsive mobile-selector-table-scroll">
            <table className="table table-sm table-hover align-middle mb-0">{head("space")}<tbody id="mobile-comedores-table-body">{spaceRows(visibleExtra, "mobile-comedores-table-body")}</tbody></table>
          </div>
          <p id="mobile-comedores-empty-state" className="text-muted small mb-0 mt-2" style={hide(!(extraSpaces.length > 0 && visibleExtra.length === 0))}>No hay espacios que coincidan con la búsqueda.</p>
        </div>
      </div>
    </>
  );
}
