/**
 * Stylesheet of `ciudadanos/ciudadano_detail.html` (the `<style>` block of the native Ciudadano 360 page),
 * copied verbatim so the React page and its cards look the same until the whole ficha migrates (C05.01).
 */
export const CIUDADANO_360_CSS = `
:root {
    --navy-dark: #232D4F;
    --navy-medium: #232D4F;
    --navy-light: #4A5F7F;
    --gold: #E7BA61;
    --green: #28A745;
    --red: #DC3545;
}

.app-content {
    background: linear-gradient(135deg, #3e5a7e 0%, #3e5a7e 100%);
    min-height: 100vh;
}

.legajo-header {
    background: #232D4F;
    padding: 1.5rem 2rem;
    border-radius: 8px;
    margin: 0 0 1rem 0;
    color: white;
    border-top: none;
    margin-left: 1rem;
    margin-right: 1rem;
}

.legajo-header h1 {
    font-family: Georgia, serif;
    font-size: 1.8rem;
    font-weight: 600;
    margin-bottom: 0;
    letter-spacing: 0.5px;
}

.legajo-header .subtitle {
    color: rgba(255,255,255,0.8);
    font-size: 0.85rem;
    font-weight: 400;
    display: none;
}

.datos-card {
    background: var(--navy-medium);
    border: 2px solid var(--gold);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    color: white;
    margin-bottom: 1rem;
}

.datos-card-content {
    display: grid;
    grid-template-columns: 220px 1fr 1fr;
    gap: 1.5rem;
}

.datos-card-simple {
    background: var(--navy-medium);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    color: white;
    margin-bottom: 1rem;
}

.datos-card-simple h5 {
    font-weight: 600;
    margin-bottom: 1rem;
}

.datos-card label, .datos-card strong {
    color: rgba(255,255,255,0.7);
    font-weight: 500;
    font-size: 0.85rem;
    display: block;
    margin-bottom: 0;
}

.datos-card .value {
    color: white;
    font-size: 0.95rem;
    display: block;
    margin-bottom: 0;
}

.datos-card .info-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.5rem;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}

.datos-card .info-row:last-child {
    border-bottom: none;
}

.info-column {
    display: flex;
    flex-direction: column;
}

.tabla-legajo {
    background: var(--navy-medium);
    border-radius: 12px;
    padding: 1.5rem;
    color: white;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.tabla-legajo h5 {
    font-weight: 600;
}

.tabla-legajo table {
    color: white;
    border-collapse: separate;
    border-spacing: 0;
}

.tabla-legajo thead {
    background: var(--navy-dark);
    border-bottom: 2px solid rgba(255,255,255,0.2);
}

.tabla-legajo thead th {
    color: white;
    font-weight: 600;
}

.tabla-legajo tbody td, .tabla-legajo tbody th {
    padding: 0.75rem 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    border-top: none;
    color: rgba(255,255,255,0.95);
}

.tabla-legajo tbody tr:hover td {
    background: rgba(255,255,255,0.05);
}

.btn-success {
    background: var(--green) !important;
    border: none !important;
}

.btn-danger {
    background: var(--red) !important;
    border: none !important;
}

.btn-outline-light:hover {
    background: rgba(255,255,255,0.1) !important;
}

.foto-placeholder {
    width: 180px;
    height: 180px;
    border-radius: 8px;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #3498DB 0%, #2980B9 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 3rem;
}

.datos-card h5 {
    margin-bottom: 1.25rem;
    font-weight: 600;
}

.nav-tabs-legajo {
    padding: 1rem 1.5rem 0.5rem 1.5rem;
    margin-bottom: 1.5rem;
    overflow-x: auto;
    white-space: nowrap;
    border-bottom: none;
    display: flex;
    gap: 0.5rem;
    background: #3e5a7e;
}

.nav-tabs-legajo .nav-link {
    background: #232D4F;
    border: none;
    border-radius: 6px;
    color: white;
    padding: 0.75rem 1.25rem;
    font-size: 0.875rem;
    transition: all 0.3s;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    height: auto;
}

.nav-tabs-legajo .nav-link.active {
    background: var(--gold);
    color: #232D4F;
    font-weight: 600;
    border: none;
}

.nav-tabs-legajo .nav-link:hover:not(.active) {
    background: rgba(255,255,255,0.1);
}

.btn-edit-card {
    position: absolute;
    top: 1rem;
    right: 1rem;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.3);
    color: white;
    width: 35px;
    height: 35px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-edit-card:hover {
    background: var(--gold);
    color: var(--navy-dark);
    border-color: var(--gold);
}

.programa-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    color: white;
}

.programa-card.auh {
    background: linear-gradient(135deg, #FF6B35 0%, #FF8C42 100%);
}

.programa-card.prestacion {
    background: linear-gradient(135deg, #FF8C42 0%, #FFB84D 100%);
}

.programa-card.centro-familia {
    background: linear-gradient(135deg, #FFB84D 0%, #FFC870 100%);
}

.programa-card.comedor {
    background: linear-gradient(135deg, #D63384 0%, #E74C9C 100%);
}

.programa-card.aduana {
    background: linear-gradient(135deg, #F8A5C2 0%, #FFC0D9 100%);
}

.programa-card .icono {
    font-size: 2rem;
    flex-shrink: 0;
}

.programa-card .info {
    flex: 1;
}

.programa-card .nombre {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 0.35rem;
}

.programa-card .monto {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: 0.5px;
}

.monto-total-widget {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    background: var(--navy-medium);
    border: 2px solid white;
    border-radius: 8px;
    padding: 1.75rem 1.5rem;
    text-align: center;
    z-index: 1000;
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    min-width: 180px;
}

.monto-total-widget small {
    display: block;
    margin-bottom: 0.75rem;
    opacity: 0.85;
    font-size: 0.8rem;
    font-weight: 500;
}

.monto-total-widget .valor {
    font-size: 2.2rem;
    font-weight: bold;
    letter-spacing: 0.5px;
}

.programas-section {
    background: var(--navy-medium);
    border-radius: 12px;
    padding: 1.5rem;
    color: white;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.programas-section h6 {
    color: white;
    font-weight: 700;
    margin-bottom: 1.25rem;
    font-size: 0.95rem;
    letter-spacing: 0.3px;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.3);
}

.historial-card {
    background: var(--navy-medium);
    border-radius: 12px;
    padding: 1.5rem;
    color: white;
    margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.historial-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}

.historial-header h6 {
    color: white;
    font-weight: 500;
    font-size: 0.95rem;
    margin: 0;
}

.periodo-selector {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.periodo-selector .btn {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.3);
    color: white;
    padding: 0.35rem 0.75rem;
    font-size: 0.8rem;
    transition: all 0.3s;
}

.periodo-selector .btn:hover {
    background: rgba(255,255,255,0.1);
    border-color: var(--gold);
}

.mes-actual {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
    padding: 0.35rem 0.75rem;
    font-size: 0.8rem;
    min-width: 120px;
    text-align: center;
}

.chart-container {
    position: relative;
    height: 600px;
    margin-top: 1rem;
}
`;
