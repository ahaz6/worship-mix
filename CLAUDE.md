# CLAUDE.md – Arbeitsregeln für KI-Agenten

- **Lies zuerst `WORSHIP_MIX.md`** (Single Source of Truth) und für UI-Arbeit **`docs/Design-Art.md`**.
- Nutzer: Agi, Junior-Dev und Tontechniker. Mit ihm sprichst du **Deutsch** und erklärst kurz das *Warum*.
- **Sichtbare UI ist komplett Englisch** (Worship-Suite-Regel). Das gilt auch für Tipp-Texte aus dem Backend.
- Design = Worship Suite / worship-keys: nur `--wm-*`-Tokens aus `frontend/app/globals.css`, keine neuen Farben.
- Live-Sicherheitsregeln (WORSHIP_MIX.md Kap. 15) sind nicht verhandelbar.
- Pult-Zugriff nur über `backend/app/consoles/base.py::ConsoleAdapter`.
- Backend: Python 3.11, FastAPI, ruff, pytest → `cd backend && pytest && ruff check .`
- Frontend: Next.js 16, React 19, TS strict, Zod, Vitest → `cd frontend && npm run verify`
- Kleine Schritte, nach jedem Meilenstein auf Bestätigung warten.
