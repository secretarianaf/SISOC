import { useEffect, type RefObject } from "react";

const FOCUSABLE = ["a", "button", "input", "textarea", "select", "details", "[tabindex]", '[contenteditable="true"]']
  .map((selector) => `${selector}:not([tabindex^="-"])`).join(",");

/**
 * Bootstrap 5.3 modal of the light layout: `modal-open` and the scrollbar padding
 * on `<body>`, focus on the dialog, its focus trap (only a focus that leaves the
 * dialog is sent back, to the first or last control by the last Tab direction),
 * Escape and a click on the backdrop close it. `returnFocus` mirrors the data API
 * (`data-bs-toggle`), which gives the focus back to its trigger; a modal opened
 * from script does not. `beforeLoad`: a modal opened on page load gets
 * `modal-open` before AdminLTE marks the body `app-loaded`.
 */
export function useBootstrapModal(modal: RefObject<HTMLDivElement | null>, close: () => void, returnFocus: HTMLElement | null, beforeLoad = false) {
  useEffect(() => {
    const body = document.body;
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    const before = { overflow: body.style.overflow, padding: body.style.paddingRight };
    if (beforeLoad && body.classList.contains("app-loaded")) body.className = body.className.replace(/\bapp-loaded\b/, "modal-open app-loaded");
    else body.classList.add("modal-open");
    body.style.overflow = "hidden";
    if (scrollbar > 0) body.style.paddingRight = `${(parseFloat(getComputedStyle(body).paddingRight) || 0) + scrollbar}px`;
    modal.current?.focus();
    let backward = false;
    const key = (event: KeyboardEvent) => {
      if (event.key === "Tab") { backward = event.shiftKey; return; }
      if (event.key === "Escape" && modal.current?.contains(document.activeElement)) { event.preventDefault(); close(); }
    };
    const focusin = (event: FocusEvent) => {
      const trap = modal.current;
      if (!trap || trap === event.target || trap.contains(event.target as Node)) return;
      const elements = Array.from(trap.querySelectorAll<HTMLElement>(FOCUSABLE))
        .filter((element) => !element.matches(":disabled") && element.getClientRects().length > 0 && getComputedStyle(element).visibility === "visible");
      if (!elements.length) trap.focus();
      else (backward ? elements[elements.length - 1] : elements[0]).focus();
    };
    document.addEventListener("keydown", key);
    document.addEventListener("focusin", focusin);
    return () => {
      document.removeEventListener("keydown", key);
      document.removeEventListener("focusin", focusin);
      body.classList.remove("modal-open");
      body.style.overflow = before.overflow;
      body.style.paddingRight = before.padding;
      returnFocus?.focus();
    };
  }, [modal, close, returnFocus, beforeLoad]);
}
