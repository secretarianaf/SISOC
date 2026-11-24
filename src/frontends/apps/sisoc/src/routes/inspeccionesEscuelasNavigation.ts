/** Full-page navigations of the Escuelas tab (native reload / 302); replaceable in tests. */
export const escuelasNavigation = {
  assign: (to: string) => window.location.assign(to),
  reload: () => window.location.reload(),
};
