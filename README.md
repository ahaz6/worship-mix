# 🎚️ Worship Mix

KI-Co-Pilot für Mixing & Mastering im Worship-Kontext – **egal welches Mischpult**.

| # | Modul | Status |
|---|---|---|
| 1 | Mix Analyzer & Coach | 🟡 Grundgerüst (LUFS, True Peak, Bänder, erste Regeln) |
| 2 | Referenz-Mastering-Pipeline | 🟡 Grundgerüst |
| 3 | Virtual Soundcheck Assistant | ⚪ geplant |
| 4 | Feedback- & Pegel-Wächter | 🟡 Detektor-Grundgerüst |
| 5 | KI-Szenen- & Preset-Bibliothek | 🟡 Presets (YAML) |
| 6 | Room Tuning (PA einmessen) | 🟢 Messen, Mitteln, Auto-EQ, GEQ/FIR/Export, RT60/C50, Sub-Abgleich |

Pult-Adapter: Mock ✅ · Allen & Heath SQ (MIDI/TCP) 🟡 · Behringer X32 (OSC) 🟡

## Dokumentation
- **[WORSHIP_MIX.md](WORSHIP_MIX.md)** – vollständige Spezifikation, Wissen, Roadmap
- **[PROMPT.md](PROMPT.md)** – Master-Prompt + Folge-Prompts für Claude Code
- **[CLAUDE.md](CLAUDE.md)** – Regeln für KI-Agenten

## Schnellstart

```bash
# Backend lokal
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# Tests
pytest

# Frontend (zweites Terminal)
cd ../frontend && npm install && npm run dev
# → http://localhost:3000

# Alles per Docker (Backend :8000, Frontend :3000)
docker compose up --build
```

Optionale Extras: `pip install -e ".[mastering,stems,live]"`

## Design
Worship Mix gehört zur **Worship Suite** und nutzt Stack und Design von [worship-keys](https://github.com/ahaz6/worship-keys): Next.js 16, React 19, TypeScript, schwarze Flächen mit Violett und Blau als Akzent, Geist-Fonts, UI auf Englisch. Details stehen in [docs/DESIGN.md](docs/DESIGN.md) und [docs/Design-Art.md](docs/Design-Art.md).
