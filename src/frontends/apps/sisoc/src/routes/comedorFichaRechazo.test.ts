import { beforeEach, describe, expect, it } from "vitest";
import { guardarRechazo, tomarRechazo } from "./comedorFichaRechazo";

const valid = (v: unknown): v is { value: string } => !!v && typeof v === "object" && typeof (v as { value?: unknown }).value === "string";

beforeEach(() => window.sessionStorage.clear());

describe("Comedor ficha: rejected post handoff", () => {
  it("hands the payload to the create page of the same endpoint and empties the storage", () => {
    expect(guardarRechazo("web/x/crear/", { value: "texto" })).toBe(true);
    expect(tomarRechazo("web/x/crear/", valid)).toEqual({ value: "texto" });
    expect(window.sessionStorage.getItem("sisoc:comedor-ficha:rechazo")).toBeNull();
    // A remount of the same page asks again and gets it; another endpoint does not, and ends it.
    expect(tomarRechazo("web/x/crear/", valid)).toEqual({ value: "texto" });
    expect(tomarRechazo("web/y/crear/", valid)).toBeNull();
    expect(tomarRechazo("web/x/crear/", valid)).toBeNull();
  });

  it("ignores a payload of another endpoint, an invalid one and a corrupt storage", () => {
    guardarRechazo("web/x/crear/", { value: "texto" });
    expect(tomarRechazo("web/y/crear/", valid)).toBeNull();
    expect(tomarRechazo("web/x/crear/", valid)).toBeNull();
    guardarRechazo("web/x/crear/", { otro: 1 });
    expect(tomarRechazo("web/x/crear/", valid)).toBeNull();
    window.sessionStorage.setItem("sisoc:comedor-ficha:rechazo", "{not json");
    expect(tomarRechazo("web/x/crear/", valid)).toBeNull();
  });

  it("reports an unavailable storage instead of throwing", () => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = () => { throw new Error("blocked"); };
    try { expect(guardarRechazo("web/x/crear/", { value: "a" })).toBe(false); } finally { Storage.prototype.setItem = original; }
  });
});
