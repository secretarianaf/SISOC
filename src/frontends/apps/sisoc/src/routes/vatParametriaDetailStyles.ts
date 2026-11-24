/** `<style>` block of `parametria_detail.html`, verbatim. */
export const PARAMETRIA_DETAIL_CSS = `
    .parametria-hero {
        background: linear-gradient(135deg, #1a3a5c 0%, #0d6efd 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: #fff;
        margin-bottom: 1rem;
    }
    .hero-label { font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; opacity: .7; }

    .assign-panel {
        border-radius: 10px;
        border: 1px solid var(--bs-border-color);
        overflow: hidden;
        background: var(--bs-card-bg);
    }
    .assign-tab {
        display: flex;
        border-bottom: 1px solid var(--bs-border-color);
        background: var(--bs-tertiary-bg);
    }
    .assign-tab button {
        flex: 1;
        padding: .6rem 1rem;
        border: none;
        background: transparent;
        font-size: .85rem;
        font-weight: 500;
        color: var(--bs-secondary-color);
        cursor: pointer;
        transition: all .15s;
        border-bottom: 2px solid transparent;
    }
    .assign-tab button.active {
        color: #0d6efd;
        border-bottom-color: #0d6efd;
        background: var(--bs-card-bg);
    }
    .assign-body { padding: 1rem; }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 3rem 1rem;
        color: var(--bs-secondary-color);
    }
    .empty-state i { font-size: 2.5rem; margin-bottom: .75rem; }
    .empty-state p { font-size: .85rem; margin: 0; }

`;
