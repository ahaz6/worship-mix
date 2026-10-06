# 🎚️ Worship Mix

KI-Co-Pilot für Mixing & Mastering im Worship-Kontext – **egal welches Mischpult**.

| # | Modul | Status |
|---|---|---|
| 1 | Mix Analyzer & Coach | 🟡 Grundgerüst (LUFS, True Peak, Bänder, erste Regeln) |
| 2 | Referenz-Mastering-Pipeline | 🟡 Grundgerüst |
| 3 | Virtual Soundcheck Assistant | ⚪ geplant |
| 4 | Feedback- & Pegel-Wächter | 🟡 Detektor-Grundgerüst |
| 5 | KI-Szenen- & Preset-Bibliothek | 🟡 Presets (YAML) |

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

# Alles per Docker
docker compose up --build
```

Optionale Extras: `pip install -e ".[mastering,stems,live]"`

## Design
Das UI übernimmt das Design von [worship-keys](https://github.com/ahaz6/worship-keys), siehe `frontend/README.md`.
