# Cola de leads · prioridad diaria

Panel para triage de leads (export de CRM, campaña de captación de compradores vía Meta Ads). Ordena los leads activos por etapa del embudo y días sin actualizar, los agrupa de 5 en 5, y separa los que están en fase "No viable" para descarte.

**Cómo prioriza:**
1. Etapa del embudo primero — Legalidad y Oferta/Negociación arriba de todo, por ser los más cerca de cerrar.
2. Dentro de la misma etapa, más días sin actualizar = más urgente (evita que un lead avanzado se enfríe).
3. Fase "No viable" o estado "lost" → van directo a la lista de descarte, separados del flujo activo.

El progreso de "atendidos" se guarda en el navegador (localStorage), no en un servidor.

## Actualizar los datos

1. Reemplazá `leads.csv` con tu export más reciente (mismas columnas en español que genera el CRM).
2. Corré:
   ```
   python3 build.py
   ```
3. Commit y push de `index.html` (y `leads.csv` si querés versionarlo).

## Estructura

- `index.html` — app publicada (GitHub Pages sirve este archivo).
- `template.html` — plantilla con el marcador `__DATA_JSON__`.
- `build.py` — arma `index.html` a partir de `leads.csv` + `template.html`.
- `leads.csv` — export de leads (contiene datos personales: nombres, teléfonos, notas).

⚠️ Este repo es público, por lo tanto `leads.csv` y los datos incrustados en `index.html` son visibles para cualquiera.
