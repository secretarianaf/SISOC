# Front v2: parches de dependencias de seguridad

Las versiones exactas de axios 1.13.5, react-router-dom 7.13.1 y Vite 7.3.1 indicadas por la primera matriz de `frontend_v2` tenían alertas en `npm audit`. Este cambio acotado actualiza respectivamente a 1.20.0, 7.18.4 y 7.3.6, junto con los transitivos resueltos en el lockfile. No modifica versiones mayores ni el runtime Node 22.14.0.

La excepción a la regla de no subir versiones en un cambio de pantallas es explícita: la aprobación de seguridad del mismo Front v2 exigía cerrar las alertas antes de integrar. Se mantiene este grupo separado de los cambios funcionales para revisión o extracción a un PR dedicado. Validar `npm ci`, `npm audit --audit-level=low`, `lint`, tipos, pruebas y build antes de promoción.
