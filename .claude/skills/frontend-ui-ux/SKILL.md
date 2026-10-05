---
name: frontend-ui-ux
description: >
  Diseño e implementación de UI/UX del frontend de SISOC: templates Django, CSS, JavaScript,
  accesibilidad (WCAG) y diseño responsive. Usar cuando la tarea sea crear o mejorar pantallas,
  componentes, estilos o la experiencia de uso, y no lógica de backend.
---

# Frontend UI/UX (SISOC)

Skill para trabajar la capa de presentación: interfaces intuitivas, accesibles y visualmente
consistentes. Convertida desde el antiguo `frontend-ui-ux.agent.md` de la raíz (#2639).

## Principios

- Priorizar buenas prácticas de experiencia (UX) e interfaz (UI).
- Usar HTML semántico para estructura y accesibilidad.
- Escribir CSS limpio y mantenible, con diseño responsive y enfoque mobile-first.
- Asegurar compatibilidad entre navegadores.
- Seguir patrones de diseño actuales y las pautas de accesibilidad (WCAG).
- Colaborar con la lógica de backend solo cuando la UI depende de ella; el foco es la
  presentación.

## Dónde trabajar en este repo

- Templates compartidos (layout, navbar, sidebar, componentes):
  `src/backends/kernel/templates/` (`includes/`, `components/`).
- Templates de un vertical: `<app>/templates/` dentro de `src/backends/<vertical>/`.
- JS/CSS compartidos: `src/backends/kernel/static/custom/`. Los de un solo vertical viven en
  `<app>/static/custom/` con la misma ruta pública (`{% static 'custom/...' %}`).
- Front v2 en React: `src/frontends/` (ver `docs/implementaciones/frontend_v2.md`). Para el tema
  de color institucional usar la skill `tema-verde-institucional`.
- Antes de crear un componente, reutilizar los de `src/backends/kernel/templates/components/`.

## Cómo trabajar

- Leer y editar templates, CSS y JS; preferir cambios chicos y localizados.
- Correr comandos de terminal solo para herramientas de frontend (por ejemplo, scripts npm del
  front v2) o para validar (`djlint`, tests de JS).
- Evitar operaciones de base de datos o lógica de servidor salvo que la UI dependa de ellas.
- Proponer mejoras de usabilidad y diseño cuando aporten, sin salir del alcance pedido.
- Respetar CSP: nada de `<script>`/`<style>` inline sin nonce (ver `docs/implementaciones/csp.md`).
