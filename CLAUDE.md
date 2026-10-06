# CLAUDE.md – Arbeitsregeln für KI-Agenten

- **Lies zuerst `WORSHIP_MIX.md`.** Sie ist die Single Source of Truth.
- Nutzer: Agi, Junior-Dev und Tontechniker. Antworte auf Deutsch und erkläre kurz das *Warum*.
- UI-Design kommt von https://github.com/ahaz6/worship-keys (siehe WORSHIP_MIX.md Kap. 5).
- Live-Sicherheitsregeln (Kap. 15) sind nicht verhandelbar.
- Pult-Zugriff nur über `backend/app/consoles/base.py::ConsoleAdapter`.
- Backend: Python 3.11, FastAPI, Type Hints, ruff, pytest. Tests: `cd backend && pytest`.
- Kleine Schritte, nach jedem Meilenstein auf Bestätigung warten.
- Neue Regeln und Presets auch in `WORSHIP_MIX.md` bzw. `presets/` dokumentieren.
