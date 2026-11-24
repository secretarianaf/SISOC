/** Full-page navigations (GET only); isolated so tests can observe them. */
export function navigateTo(url: string): void {
  window.location.assign(url);
}

export function replaceWith(url: string): void {
  window.location.replace(url);
}
