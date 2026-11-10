import { expect, test, type Page } from "@playwright/test";

const base = process.env.INET_PLAYWRIGHT_BASE_URL || "http://127.0.0.1:4175";
const item = { id: 1, nombre: "CFP de prueba", cue: "060144900", provincia: "Buenos Aires", localidad: "Tolosa", estado: "Activo", centro_id: 1, detalle: [{ label: "Domicilio", value: "Calle de prueba 123" }], puede_gestionar: true, puede_editar: true, puede_eliminar: false, comisiones_count: 0 };
const pageData = { count: 1, next: null, previous: null, results: [item] };
async function prepare(page: Page) {
  await page.route("https://www.google.com/maps**", route => route.fulfill({ contentType: "text/html", body: "<!doctype html><title>Mapa de prueba</title><p>Mapa de prueba</p>" }));
  await page.context().addCookies([{ name: "csrftoken", value: "inet-test-csrf", url: base }]);
  await page.route("**/v2/inet/**", async route => {
    if (route.request().resourceType() !== "document") return route.continue();
    const response = await route.fetch();
    await route.fulfill({ response, headers: { ...response.headers(), "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-src 'self' https://www.google.com https://maps.google.com" } });
  });
  await page.route("**/api/inet/**", route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("session/")) return route.fulfill({ json: { username: "operador", nombre: "Operador de prueba", permissions: ["view_centro", "add_centro", "view_curso", "view_comisioncurso"], puede_ver_planes: true } });
    if (path.endsWith("filter-form/")) return route.fulfill({ json: { fields: [] } });
    if (path.endsWith("centros/form/")) return route.fulfill({ json: { fields: [{ name: "nombre", label: "Denominación", kind: "text", required: true, disabled: false, value: "", options: [], remote_options: false, help_text: "" }] } });
    if (path.endsWith("centros/1/")) return route.fulfill({ json: item });
    if (path.endsWith("centros/") && route.request().method() === "POST") return route.fulfill({ status: 400, json: { nombre: ["La denominación no es válida."] } });
    return route.fulfill({ json: path.endsWith("centros/") ? pageData : { ...pageData, count: 0, results: [] } });
  });
}
test("INET: navegación, CSP, tema y formulario con CSRF", async ({ page }) => {
  await prepare(page);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(`${base}/v2/inet/`);
  await expect(page.getByRole("heading", { name: "Buscar Centro de Formación Profesional" })).toBeVisible();
  await page.getByRole("button", { name: "Agregar CFP" }).click();
  await page.getByLabel("Denominación").fill("Prueba");
  const request = page.waitForRequest(request => request.method() === "POST");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  expect((await request).headers()["x-csrftoken"]).toBe("inet-test-csrf");
  await expect(page.getByText("La denominación no es válida.", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await page.screenshot({ path: "test-results/inet-claro.png", fullPage: true });
  await page.getByRole("button", { name: "Activar modo oscuro" }).click();
  await expect(page.getByRole("button", { name: "Activar modo claro" })).toBeVisible();
  await page.getByRole("button", { name: "Ver CFP de prueba" }).click();
  await expect(page).toHaveURL(/centros\/1\//);
  await expect(page.getByText("Calle de prueba 123")).toBeVisible();
  await expect(page.getByTitle("Mapa de la sede: CFP de prueba")).toHaveAttribute("src", /q=Calle%20de%20prueba%20123%2C%20Tolosa%2C%20Buenos%20Aires%2C%20Argentina/);
  await page.screenshot({ path: "test-results/inet-oscuro.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("tab", { name: "Ubicaciones" })).toBeVisible();
  await page.screenshot({ path: "test-results/inet-movil.png", fullPage: true });
  expect(errors).toEqual([]);
});
