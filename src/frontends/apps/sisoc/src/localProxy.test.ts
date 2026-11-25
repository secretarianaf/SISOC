// @vitest-environment node
import { describe, expect, it } from "vitest";
import { createServer as createHttpServer } from "node:http";
import { once } from "node:events";
import { createServer as createViteServer } from "vite";
import sisocViteConfig from "../vite.config";

describe("local legacy navigation proxy", () => {
  it("preserves the browser Host and Origin on cookie-authenticated API POSTs", async () => {
    const route = sisocViteConfig.server?.proxy?.["/api/web"];
    const upstream = createHttpServer((request, response) => {
      const sameOrigin = request.headers.origin === `http://${request.headers.host}`;
      response.writeHead(sameOrigin ? 200 : 403, { "content-type": "application/json" });
      response.end(JSON.stringify({ method: request.method, path: request.url, csrfPresent: !!request.headers["x-csrftoken"] }));
    });
    upstream.listen(0, "127.0.0.1");
    await once(upstream, "listening");
    const address = upstream.address();
    if (!address || typeof address === "string") throw new Error("No synthetic upstream port");
    const target = `http://127.0.0.1:${address.port}`;
    const vite = await createViteServer({
      ...sisocViteConfig, configFile: false, root: process.cwd(),
      server: { ...sisocViteConfig.server, port: 0, strictPort: false, proxy: { "/api/web": typeof route === "string" ? target : { ...route, target } } },
    });
    try {
      await vite.listen();
      const bound = vite.httpServer?.address();
      if (!bound || typeof bound === "string") throw new Error("No synthetic Vite port");
      const origin = `http://127.0.0.1:${bound.port}`;
      const response = await fetch(`${origin}/api/web/insumos/crear/`, { method: "POST", headers: { Origin: origin, "X-CSRFToken": "synthetic-only" } });
      expect(response.status).toBe(200);
      expect(await response.json()).toEqual({ method: "POST", path: "/api/web/insumos/crear/", csrfPresent: true });
    } finally {
      await vite.close();
      await new Promise<void>((resolve, reject) => upstream.close((error) => error ? reject(error) : resolve()));
    }
  });
  it("forwards Django routes without changing origin while keeping app/API/static paths local", () => {
    const proxy = sisocViteConfig.server?.proxy ?? {};
    const legacyEntry = Object.entries(proxy).find(([context]) => context.startsWith("^/"));

    expect(legacyEntry).toBeDefined();
    const [pattern, options] = legacyEntry ?? ["", ""];
    const isLegacyRoute = new RegExp(pattern).test.bind(new RegExp(pattern));

    for (const path of ["/login/", "/logout/", "/inicio/", "/mi-cuenta/", "/password/first-change/"]) {
      expect(isLegacyRoute(path), path).toBe(true);
    }
    for (const path of ["/v2/sisoc/insumos/", "/api/web/session/", "/static/custom/img/logoBlanco.png"]) {
      expect(isLegacyRoute(path), path).toBe(false);
    }

    expect(options).toMatchObject({ target: "http://127.0.0.1:18885", changeOrigin: false });
  });

  it("serves base-prefixed local CSS through Django static instead of the Vite HTML fallback", async () => {
    const proxy = sisocViteConfig.server?.proxy ?? {};
    const staticRoute = proxy["/v2/sisoc/static/"];
    expect(staticRoute).toBeDefined();
    if (!staticRoute || typeof staticRoute === "string" || !staticRoute.rewrite) {
      throw new Error("The base-prefixed static route needs a rewrite handler.");
    }

    let receivedPath = "";
    const upstream = createHttpServer((request, response) => {
      receivedPath = request.url ?? "";
      if (receivedPath === "/static/custom/css/listModerno.css") {
        response.writeHead(200, { "content-type": "text/css" });
        response.end(".legacy-list-marker { display: block; }");
        return;
      }
      response.writeHead(404, { "content-type": "text/html" });
      response.end("<!doctype html><title>Not found</title>");
    });
    upstream.listen(0, "127.0.0.1");
    await once(upstream, "listening");
    const upstreamAddress = upstream.address();
    if (!upstreamAddress || typeof upstreamAddress === "string") {
      throw new Error("The synthetic static server did not bind a TCP port.");
    }

    const vite = await createViteServer({
      ...sisocViteConfig,
      configFile: false,
      root: process.cwd(),
      server: {
        ...sisocViteConfig.server,
        host: "127.0.0.1",
        port: 0,
        strictPort: false,
        proxy: {
          ...proxy,
          "/v2/sisoc/static/": {
            ...staticRoute,
            target: `http://127.0.0.1:${upstreamAddress.port}`,
          },
        },
      },
    });

    try {
      await vite.listen();
      const viteAddress = vite.httpServer?.address();
      if (!viteAddress || typeof viteAddress === "string") {
        throw new Error("The synthetic Vite server did not bind a TCP port.");
      }
      const result = await fetch(
        `http://127.0.0.1:${viteAddress.port}/v2/sisoc/static/custom/css/listModerno.css`,
      );
      expect(result.status).toBe(200);
      expect(result.headers.get("content-type")).toContain("text/css");
      expect(await result.text()).toContain(".legacy-list-marker");
      expect(receivedPath).toBe("/static/custom/css/listModerno.css");
    } finally {
      await vite.close();
      await new Promise<void>((resolve, reject) => {
        upstream.close((error) => (error ? reject(error) : resolve()));
      });
    }
  });
});
