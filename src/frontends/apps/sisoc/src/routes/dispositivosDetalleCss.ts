/** Inline `<style>` of `dispositivos_detail.html` (head block), copied verbatim. */
export const DETALLE_CSS = `
.detail-item-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #64748b;
    margin-bottom: 4px;
}
.detail-item-value {
    font-size: 14px;
    color: #e2e8f0;
    word-break: break-word;
    line-height: 1.5;
}
.detail-item-value.empty {
    color: #3d4f63;
}
.chip-list {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 2px;
}
.chip {
    display: inline-flex;
    align-items: center;
    background: #1e3a5f;
    border: 1px solid #2d5280;
    color: #93c5fd;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 12px;
    line-height: 1.5;
}
.doc-card-ro {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: #202f40;
    border: 1px solid #2d4a6a;
    border-radius: 8px;
    padding: 8px 14px;
    text-decoration: none;
    color: #cbd5e1;
    font-size: 13px;
    transition: background 0.2s, border-color 0.2s, color 0.2s;
}
.doc-card-ro:hover {
    background: #253a52;
    border-color: #f39c12;
    color: #f39c12;
    text-decoration: none;
}
.doc-card-ro .doc-card-icon { font-size: 20px; flex-shrink: 0; }
.doc-card-ro .doc-card-icon.pdf { color: #e74c3c; }
.doc-card-ro .doc-card-icon.img { color: #3498db; }
.doc-card-ro .doc-card-name {
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.doc-cards-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}
.docs-section-divider {
    border-top: 1px solid #2d3f52;
    margin: 20px 0 14px;
}
.docs-section-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #64748b;
    margin: 12px 0 10px;
}
.detail-page-header {
    background: #1a2535;
    border: 1px solid #2d3f52;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 20px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
}
.detail-page-title {
    font-size: 22px;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0 0 6px 0;
    line-height: 1.2;
}
.detail-page-meta {
    font-size: 13px;
    color: #64748b;
}
.detail-page-meta span { color: #94a3b8; }
.section-body-detail {
    padding: 20px 0 4px;
}
.section-body-detail .row {
    row-gap: 18px;
    padding: 8px 28px 28px 28px;
    }
/* Quita el chevron en modo detalle */
.section-card .collapse-indicator { display: none; }
/* Cards al tono de comedor_detail */
.section-card {
    background: #232d4f;
    border: 1px solid #2d3f5e;
}
.section-header {
    background: #1a2340 !important;
    border-bottom: 1px solid #2d3f5e;
}
.section-header:hover {
    background: #1f2b4d !important;
}
.section-body-detail {
    background: #232d4f;
}
/* Header de página al mismo tono */
.detail-page-header {
    background: #1a2340;
    border-color: #2d3f5e;
}
`;
