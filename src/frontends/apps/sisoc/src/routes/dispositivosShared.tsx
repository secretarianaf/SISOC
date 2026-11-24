/* eslint-disable react-refresh/only-export-components -- shared pieces of the Dispositivos screens (list and map). */
import { internal, record, text } from "./cdfFrame";
import type { Favorites } from "./cdfFilters";

export const favoritesValid = (v: unknown): v is Favorites => record(v) && text(v.section) && internal(v.url) && internal(v.detail_url_template);

/** `components/search_bar.html` actions row: map link, Resetear and the add button. */
export function SearchActions({ mapUrl, mapText, resetUrl, addUrl, addText }: { mapUrl: string | null; mapText: string; resetUrl: string; addUrl: string | null; addText: string }) {
  return (
    <div className="row mt-3">
      <div className="col-12 d-flex flex-wrap justify-content-end gap-2 search-actions">
        {mapUrl && <a href={mapUrl} className="poncho-btn poncho-btn--cta me-auto"><i className="fas fa-map-marked-alt" aria-hidden="true" />{mapText}</a>}
        <a href={resetUrl} className="poncho-btn poncho-btn--neutro" data-restablecer-filtros-favoritos="true">Resetear</a>
        {addUrl && <a href={addUrl} className="poncho-btn poncho-btn--cta"><i className="fas fa-plus" aria-hidden="true" />{addText}</a>}
      </div>
    </div>
  );
}
