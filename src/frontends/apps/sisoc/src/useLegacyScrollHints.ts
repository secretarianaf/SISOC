import { useLayoutEffect, useRef, useState } from "react";

const LEGACY_SCROLL_MARGIN = 2;

export function useLegacyScrollHints(revision: string | null) {
  const cardRef = useRef<HTMLDivElement>(null);
  const tableRef = useRef<HTMLDivElement>(null);
  const [classes, setClasses] = useState({ card: "poncho-scroll", table: "poncho-scroll" });

  useLayoutEffect(() => {
    const card = cardRef.current;
    const table = tableRef.current;
    if (!card || !table) return undefined;
    let active = true;
    const describe = (element: HTMLDivElement) => {
      const overflow = element.scrollWidth - element.clientWidth > LEGACY_SCROLL_MARGIN;
      const left = overflow && element.scrollLeft > LEGACY_SCROLL_MARGIN;
      const right = overflow &&
        element.scrollLeft + element.clientWidth < element.scrollWidth - LEGACY_SCROLL_MARGIN;
      return `poncho-scroll${left ? " poncho-scroll--izq" : ""}${right ? " poncho-scroll--der" : ""}`;
    };
    const update = () => {
      if (!active) return;
      const next = { card: describe(card), table: describe(table) };
      setClasses((current) => (
        current.card === next.card && current.table === next.table ? current : next
      ));
    };
    update();
    card.addEventListener("scroll", update, { passive: true });
    table.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(update) : null;
    observer?.observe(card);
    observer?.observe(table);
    return () => {
      active = false;
      observer?.disconnect();
      card.removeEventListener("scroll", update);
      table.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [revision]);

  return { cardRef, tableRef, classes };
}
