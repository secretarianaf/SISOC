import { expect, test, type Page } from "@playwright/test";

const session = { username: "Provincia", can_view_itinerarios: true, can_view_sedes: true, can_export: false, permissions: {} };

async function prepare(page: Page) {
  await page.context().addCookies([{ name: "csrftoken", value: "test-csrf", url: test.info().project.use.baseURL! }]);
  await page.route("**/v2/vpsl/**", async (route) => {
    if (route.request().resourceType() !== "document") return route.continue();
    const response = await route.fetch();
    await route.fulfill({ response, headers: { ...response.headers(), "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'" } });
  });
  await page.route("**/api/vpsl/session/", (route) => route.fulfill({ json: session }));
}

test("subsanación: instrucciones, carta actual y carga de corrección bajo CSP", async ({ page }) => {
  await prepare(page);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/vpsl/forms/itinerario-subsanar/1/", (route) => route.fulfill({ json: {
    kind: "itinerario-subsanar", back: "itinerarios/1/", instrucciones: "Adjuntar carta firmada.", fields: [{
      name: "carta_archivo", label: "Nueva carta", type: "file", required: true, disabled: false,
      help: "", value: "", choices: [], min: "", max: "", step: "", graduacion_opcional: false, file_url: "/media/carta.pdf",
    }],
  } }));
  await page.goto("/v2/vpsl/forms/itinerario-subsanar/1/");
  await expect(page.getByText(/Adjuntar carta firmada/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Ver archivo actual" })).toHaveAttribute("href", "/media/carta.pdf");
  await page.getByLabel("Nueva carta").setInputFiles({ name: "firmada.pdf", mimeType: "application/pdf", buffer: Buffer.from("firma") });
  const sent = page.waitForRequest((request) => request.method() === "POST");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  const request = await sent;
  expect(request.headers()["content-type"]).toContain("multipart/form-data");
  expect(request.headers()["x-csrftoken"]).toBe("test-csrf");
  expect(request.postData()).toContain("firmada.pdf");
  expect(errors).toEqual([]);
});

test("formularios sin archivo usan JSON con CSRF", async ({ page }) => {
  await prepare(page);
  await page.route("**/api/vpsl/forms/sede-create/0/", (route) => route.fulfill({ json: {
    kind: "sede-create", back: "sedes/", instrucciones: "", fields: [{
      name: "nombre", label: "Nombre", type: "text", required: true, disabled: false,
      help: "", value: "", choices: [], min: "", max: "", step: "", graduacion_opcional: false, file_url: "",
    }],
  } }));
  await page.goto("/v2/vpsl/forms/sede-create/0/");
  await page.getByLabel("Nombre").fill("Escuela de prueba");
  const sent = page.waitForRequest((request) => request.method() === "POST");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  const request = await sent;
  expect(request.headers()["content-type"]).toContain("application/json");
  expect(request.headers()["x-csrftoken"]).toBe("test-csrf");
  expect(request.postDataJSON()).toEqual({ nombre: "Escuela de prueba" });
});

test("403 con sesión muestra sin permiso y conserva la ruta", async ({ page }) => {
  await prepare(page);
  await page.route("**/api/vpsl/itinerarios/1/", (route) => route.fulfill({ status: 403, json: { detail: "Sin permiso" } }));
  await page.goto("/v2/vpsl/itinerarios/1/");
  await expect(page.getByRole("heading", { name: "Sin permiso" })).toBeVisible();
  await expect(page).toHaveURL(/v2\/vpsl\/itinerarios\/1\//);
});
