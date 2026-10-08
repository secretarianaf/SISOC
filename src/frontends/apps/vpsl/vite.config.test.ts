import { expect, it } from "vitest";
import { createServer } from "vite";
import { fileURLToPath } from "node:url";

it("sirve Fast Refresh sin scripts inline y con el base de Django", async () => {
  const server = await createServer({
    root: fileURLToPath(new URL(".", import.meta.url)),
    configFile: fileURLToPath(new URL("./vite.config.ts", import.meta.url)),
    server: { port: 0, host: "127.0.0.1" },
    optimizeDeps: { noDiscovery: true, include: [] },
  });
  try {
    await server.listen();
    const address = server.httpServer!.address();
    if (!address || typeof address === "string") throw new Error("Missing Vite port");
    const origin = `http://127.0.0.1:${address.port}`;
    const html = await (await fetch(`${origin}/v2/vpsl/`)).text();
    expect(html).not.toMatch(/<script[^>]*>(?!\s*<\/script>)[\s\S]*?window\.\$RefreshReg\$/);
    expect(html).toContain('src="/v2/vpsl/react-refresh-preamble.js"');
    const preamble = await fetch(`${origin}/v2/vpsl/react-refresh-preamble.js`);
    expect(preamble.status).toBe(200);
    expect(await preamble.text()).toContain('"/v2/vpsl/@react-refresh"');
  } finally { await server.close(); }
}, 20000);
