import { useEffect } from "react";

/**
 * Body state of the native Bootstrap modals of `comedor_detail.html`, which `NativeModal` does not
 * reproduce by itself.
 *
 * `useBodyLock`: an open modal leaves `<body style="overflow: hidden; padding-right: 0px">`.
 */
export function useBodyLock() {
  useEffect(() => {
    const { overflow, paddingRight } = document.body.style;
    document.body.style.overflow = "hidden";
    document.body.style.paddingRight = "0px";
    return () => { document.body.style.overflow = overflow; document.body.style.paddingRight = paddingRight; };
  }, []);
}

/**
 * `mostrarOpcionesNoValidar` hides the first modal and shows the second at once: when the first
 * backdrop finishes hiding Bootstrap removes `modal-open` and the scroll lock although the second
 * modal is open. The second modal therefore shows with neither. Runs after the trap of `NativeModal`
 * (child effects go first), on every render, because the trap re-adds the class when it re-runs.
 */
export function useModalOpenOff() {
  useEffect(() => { document.body.classList.remove("modal-open"); });
}
