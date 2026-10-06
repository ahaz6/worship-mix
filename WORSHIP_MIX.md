# 🎚️ Worship Mix – Vollständige Spezifikation, Wissen & Instruktionen

> **KI-gestütztes Mixing & Mastering für Worship-Teams – egal welches Mischpult.**
> Dieses Dokument ist die *Single Source of Truth* für Menschen und KI-Agenten (Claude Code etc.).
> Wer an Worship Mix arbeitet, liest zuerst diese Datei.

---

## Inhaltsverzeichnis

1. [Vision & Zielgruppe](#1-vision--zielgruppe)
2. [Die Module im Überblick](#2-die-module-im-überblick)
3. [Architektur](#3-architektur)
4. [Tech-Stack](#4-tech-stack)
5. [UI-Design: Übernahme von worship-keys](#5-ui-design-übernahme-von-worship-keys)
6. [Modul 1 – Mix Analyzer & Coach](#6-modul-1--mix-analyzer--coach)
7. [Modul 2 – Referenz-Mastering-Pipeline](#7-modul-2--referenz-mastering-pipeline)
8. [Modul 3 – Virtual Soundcheck Assistant](#8-modul-3--virtual-soundcheck-assistant)
9. [Modul 4 – Feedback- & Pegel-Wächter](#9-modul-4--feedback---pegel-wächter)
10. [Modul 5 – KI-Szenen- & Preset-Bibliothek](#10-modul-5--ki-szenen---preset-bibliothek)
11. [Console-Adapter (Pult-Unabhängigkeit)](#11-console-adapter-pult-unabhängigkeit)
11a. [Modul 6 – Room Tuning (Einmessen der PA)](#11a-modul-6--room-tuning-einmessen-der-pa)
11b. [Modul 3 – Instruments (Instrument & Mix Tuning)](#11b-modul-3--instruments-instrument--mix-tuning)
12. [Audio-Fachwissen (Knowledge Base)](#12-audio-fachwissen-knowledge-base)
13. [Worship-spezifisches Wissen](#13-worship-spezifisches-wissen)
14. [KI-Strategie (Regeln + ML + LLM)](#14-ki-strategie-regeln--ml--llm)
15. [Sicherheit im Live-Betrieb](#15-sicherheit-im-live-betrieb)
16. [API-Design](#16-api-design)
17. [Datenmodell](#17-datenmodell)
18. [Roadmap & Meilensteine](#18-roadmap--meilensteine)
19. [Coding-Konventionen & Tests](#19-coding-konventionen--tests)
20. [Glossar](#20-glossar)
21. [Quellen & Referenzen](#21-quellen--referenzen)

---

## 1. Vision & Zielgruppe

**Problem:** In vielen Gemeinden mischen Ehrenamtliche mit wenig Erfahrung. Jeden Sonntag gibt es andere Besetzungen, wenig Soundcheck-Zeit, Rückkopplungen und einen Mix, der „irgendwie“ klingt. Gute Aufnahmen (Livestream, Worship-Releases) brauchen dann noch Mixing und Mastering, und dafür fehlt Zeit oder Know-how.

**Lösung:** Worship Mix ist ein **KI-Co-Pilot für den Tontechniker**:

- **Im Studio:** Analysiert Mixe, gibt konkrete Tipps und mastert automatisch.
- **Live:** Unterstützt den Soundcheck, warnt vor Feedback und erstellt Startszenen.
- **Pult-unabhängig:** Eine KI-Logik und austauschbare Adapter (Allen & Heath SQ, Behringer X32/Wing, später Yamaha, Midas und weitere).

**Leitprinzipien:**

1. **Mensch entscheidet, KI schlägt vor.** Live wird nie ohne Bestätigung oder klar definierte Grenzen etwas am Pult verändert.
2. **Erklären statt nur machen.** Jeder Vorschlag hat ein *Warum*. Ehrenamtliche sollen dabei lernen.
3. **Offline-fähig.** Gemeinde-WLAN ist unzuverlässig, daher muss alles Kritische lokal laufen.
4. **Worship-first.** Vocals und Textverständlichkeit stehen über allem, die Gemeinde soll mitsingen können.

**Zielgruppe:**

| Persona | Bedürfnis |
|---|---|
| Ehrenamtlicher Techniker (Anfänger) | Startszenen, einfache Tipps, Feedback-Warnung |
| Erfahrener FOH / Agi | Zeit sparen, Automatisierung, präzise Analyse |
| Worship-Band / Produzent | Studio-Mix-Feedback, schnelles Mastering für Releases |
| Livestream-Team | Lautheitsziele, konsistenter Broadcast-Mix |

---

## 2. Die Module im Überblick

| # | Modul | Kontext | Input | Output | Pult nötig? |
|---|---|---|---|---|---|
| 1 | **Mix Analyzer & Coach** | Studio + Live-Mitschnitt | Mix/Stems (WAV/FLAC/MP3) | Metriken + konkrete Tipps | ❌ |
| 2 | **Referenz-Mastering** | Studio / Release | Track + Referenz | Master-Dateien (mehrere Loudness-Ziele) | ❌ |
| 3 | **Instruments** (Instrument & Mix Tuning, Kap. 11b) | Soundcheck + Live | Demo, Upload oder Live-USB | Gain/HPF/EQ/Gate/Comp/De-Esser/FX pro Kanal, Fader, Sidechain, Master → Pult | ✅ (optional) |
| 4 | **Feedback- & Pegel-Wächter** | Live (Echtzeit) | Audio-Input (Interface) | Warnungen, optional Auto-Notch | ✅ (optional) |
| 5 | **Szenen- & Preset-Bibliothek** | Vorbereitung | Besetzung in Textform | Startszene, Presets, Kanalliste | ✅ (optional) |
| 6 | **Room Tuning** | Einmessen der PA | Sweep-Aufnahmen mehrerer Plätze | Raum-EQ (PEQ/GEQ/FIR), RT60/C50, Sub-Delay | ❌ (Export), ✅ optional |

**Synergien:**

- Modul 1 liefert die **Analyse-Engine**, die Modul 2, 3 und 4 wiederverwenden.
- Modul 5 erzeugt Szenen, die Modul 3 nach dem Soundcheck **verfeinert**.
- Alle Pult-Aktionen laufen über **eine** Adapter-Schnittstelle (Kapitel 11).

---

## 3. Architektur

```
┌──────────────────────────────────────────────────────────────┐
│        Frontend: Next.js 16 / React 19 / TS (PWA)            │
│        Worship-Suite-Design · Tablet-/Handy-tauglich         │
└───────────────▲──────────────────────────────▲───────────────┘
                │ REST (Uploads, Jobs)         │ WebSocket (Live-Meter, Alerts)
┌───────────────┴──────────────────────────────┴───────────────┐
│                     Backend (FastAPI, Python)                │
│ ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌────────┐ ┌───────┐│
│ │ analysis │ │ mastering │ │ soundcheck│ │  live  │ │presets││
│ └────┬─────┘ └─────┬─────┘ └─────┬─────┘ └───┬────┘ └───┬───┘│
│      └─────────────┴──── Core DSP ┴───────────┘          │    │
│                  (numpy, librosa, pyloudnorm,             │    │
│                   pedalboard, demucs, matchering)         │    │
│ ┌────────────────────────────────────────────────────────▼──┐ │
│ │      Console Abstraction Layer (ConsoleAdapter)           │ │
│ │   SQ (MIDI/TCP) · X32 (OSC/UDP) · Wing (OSC) · Mock       │ │
│ └───────────────────────────────────────────────────────────┘ │
│ ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│ │ Job-Queue    │  │ SQLite/      │  │ LLM-Layer (Claude)   │  │
│ │ (RQ/arq)     │  │ Postgres     │  │ Erklärungen, Szenen  │  │
│ └──────────────┘  └──────────────┘  └─────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                │ Netzwerk (LAN am Pult)
        ┌───────▼────────┐
        │  Mischpult     │
        └────────────────┘
```

**Wichtige Entscheidungen:**

- **Python-Backend**, weil das Audio-/ML-Ökosystem dort am stärksten ist.
- **Lange Jobs** (Stem-Separation, Mastering) laufen asynchron über eine Job-Queue, das Frontend pollt oder bekommt WebSocket-Updates.
- **Echtzeit-Teil** (Modul 4) läuft als eigener Prozess mit `sounddevice` und Ringbuffer. Er darf nie vom HTTP-Server blockiert werden.
- **LLM ist optional.** Alle Kernfunktionen laufen ohne LLM über eine Regel-Engine. Das LLM formuliert Erklärungen und erzeugt Szenen aus Freitext.
- **Deployment:** Lokal per `docker compose up` auf einem Laptop am FOH. Optional später Cloud/Kubernetes für Modul 1 und 2.

---

## 4. Tech-Stack

| Bereich | Wahl | Warum |
|---|---|---|
| Backend | **Python 3.11+, FastAPI, Uvicorn** | Async, schnell, Typen via Pydantic |
| DSP / Analyse | **numpy, scipy, librosa, pyloudnorm, soundfile** | Standard, gut dokumentiert |
| Effekte/Plugins | **pedalboard** (Spotify) | EQ/Kompressor/Limiter + VST3-Hosting in Python |
| Stem-Separation | **Demucs (htdemucs)** | State of the Art, lokal |
| Referenz-Mastering | **matchering** | Open Source, Python |
| Live-Audio | **sounddevice** (PortAudio) | Interface-Zugriff, niedrige Latenz |
| Pult-Protokolle | **python-osc**, rohes **TCP/MIDI** (eigene Implementierung) | X32/Wing via OSC, SQ via MIDI-over-TCP |
| Jobs | **arq** (Redis) oder **RQ** | einfach |
| DB | **SQLite** (lokal), Postgres (Cloud) via SQLModel | |
| LLM | **Claude API** (optional, per Env-Var) | Erklärungen, Szenen aus Text |
| Frontend | **Next.js 16, React 19, TypeScript, reines CSS, Zod** (wie worship-keys, Kap. 5.1) | einheitlich in der Worship Suite |
| Visualisierung | Canvas für Spektrum & Meter, CSS für statische Meter | Performance |
| Tests | **pytest**, synthetische Testsignale | reproduzierbar |
| Packaging | Docker + docker compose | Ein Befehl zum Starten |

---

## 5. UI-Design: Übernahme von worship-keys

**Quelle:** https://github.com/ahaz6/worship-keys. Verbindlich sind `Design-Art.md` (liegt als Kopie in `docs/Design-Art.md`) und `app/globals.css`.

Worship Mix ist das nächste Produkt der **Worship Suite** (Worship Loops, Worship Keys, Worship Mix). Es muss sofort als Teil der Familie erkennbar sein, darf aber kein umbenannter Klon sein.

> Leitidee der Suite: **„A calm, premium, black-led worship workspace with restrained violet and blue light.“**

### 5.1 Stack (identisch zu worship-keys)

| Bereich | Wahl |
|---|---|
| Framework | **Next.js 16 (App Router), React 19, TypeScript 5.9** (strict, `noUncheckedIndexedAccess`) |
| Styling | **Reines CSS** in `app/globals.css` mit CSS-Variablen, kein Tailwind |
| Fonts | **Geist Sans** (UI) und **Geist Mono** (Zahlen, dB, LUFS, Hz) über `next/font/google` |
| Validierung | **Zod 4** für alle Daten vom Backend |
| Tests | **Vitest** (Unit), **Playwright** (E2E, später) |
| Lint | ESLint 9 mit `eslint-config-next` |
| Node | ≥ 22.13 |
| Pfad-Alias | `@/*` |

### 5.2 Design-Tokens

Die Werte sind **identisch** zu worship-keys (Design-Art.md 5.3), nur das Präfix ändert sich zu `--wm-`:

```css
:root {
  color-scheme: dark;
  --wm-bg-deep: #09090c;   --wm-bg: #0d0d12;
  --wm-panel: #121216;     --wm-panel-raised: #17171e;  --wm-panel-active: #20202a;
  --wm-text: #efeff4;      --wm-text-soft: #b5b3c1;     --wm-text-muted: #85858f;  --wm-text-faint: #62626c;
  --wm-line: #292931;      --wm-line-strong: #353541;
  --wm-violet: #7668b7;    --wm-violet-bright: #9d8cff; --wm-indigo: #4e5fc6;      --wm-blue: #5d7fe6;
  --wm-cyan-muted: #5b929d;
  --wm-success: #67a89e;   --wm-warning: #c89b61;       --wm-danger: #c76f7b;
  --wm-radius-control: 9px; --wm-radius-card: 14px; --wm-radius-modal: 20px;
  --wm-motion: 170ms; --wm-ease: cubic-bezier(0.32, 0.72, 0.35, 1);
}
```

**Hintergrund:** Schwache radiale Violett/Blau-Lichtfelder über fast schwarzem Verlauf und ein statisches, kaum sichtbares Sternenfeld (Opacity 0.06, nie animiert).

**Farbbedeutung, übertragen auf Mixing:**

| Farbe | Worship Keys | Worship Mix |
|---|---|---|
| Violett | Primäraktion, aktive Tonart | Primäraktion, aktives Modul, Zielwert-Markierung (LUFS-Ziel) |
| Blau/Indigo | MIDI-Aktivität, vorbereitet | Info-Tipps, Pult-Aktivität, vorbereitete Szene |
| Gedämpftes Cyan/Grün | verbunden/bereit | Pult verbunden, Meter im grünen Bereich |
| Orange | Warnung | Tipp „Check“, Meter heiß, Maskierung |
| Rot | Fehler, destruktiv | Tipp „Fix“, Clipping, **Feedback-Alarm**, Kill-Switch |

Farbe ist **nie** die einzige Information. Es gibt immer auch Text oder ein Symbol, z. B. `● Connected — SQ-Rack 192.168.1.70`.

### 5.3 Typografie
- Labels: 10–11 px, uppercase, Tracking 0.16–0.17 em (`.label`, `.section-title`)
- Technische Werte (dB, LUFS, Hz, Kanalnummern): **Geist Mono**, `tabular-nums`
- Modultitel: `clamp(24px, 2.6vw, 32px)`
- Live-Information (z. B. Feedback-Frequenz): groß, gut lesbar aus zwei Metern Entfernung

### 5.4 Layout: Shell mit drei Bereichen

```text
┌──────────────────┬────────────────────────────────┬───────────────────┐
│ Brand            │ Stage: aktives Modul           │ Console           │
│ WORSHIP / MIX    │ (Analyzer, Mastering, …)       │ Verbindung, Write │
│ Modul-Navigation │                                │ Live Guard        │
│ 01–06            │                                │ Kill-Switch       │
└──────────────────┴────────────────────────────────┴───────────────────┘
  268 px            flexibel, min. 560 px            300 px
```

- **Linke Rail:** Statt der Setlist von Worship Keys steht hier die Modul-Navigation (`01 Mix Analyzer` … `06 Room Tuning`).
- **Rechte Rail:** Pult und Sicherheit. Der Kill-Switch ist **immer** sichtbar.
- **≤ 1180 px:** Die rechte Rail wandert unter die Stage.
- **≤ 820 px (Handy/Tablet hochkant):** Alles einspaltig, die Navigation wird horizontal scrollbar.
- Touch-Ziele mindestens 44 × 44 px, `prefers-reduced-motion` wird respektiert.

### 5.5 Brand
- Wortmarke zweizeilig: `WORSHIP` / `MIX`, Großbuchstaben, Verlauf von fast Weiß zu hellem Violett und Blau (wie `BrandMark` in worship-keys).
- **Logo:** Ein eigenes rundes Produktlogo ist Pflicht (Design-Art 3.1). Aktuell gibt es nur einen Platzhalter (stilisierte Fader im Kreis). **TODO:** `Worship Mix Icon.png` erstellen, nach `public/worship-mix-icon.png` legen, Favicon und App-Icons (`app/icon.png`, `app/apple-icon.png`) ableiten.

### 5.6 Übernommene Komponenten
`BrandMark`, `Status` (Dot + Zustand + Detail), `.btn-primary`, `.btn` (inkl. `tone-quiet`, `tone-danger`, `is-active`), `.panel-card`, `.field`/`.field-head`, `.slider`, Inputs/Selects, `.modal`, `.label`, `.section-title`, `.hint`, `.meta`.

### 5.7 Neue Worship-Mix-Komponenten (gleiche Tokens, neuer Inhalt)

| Komponente | Zweck | Status |
|---|---|---|
| `LevelMeter` | LUFS/Peak-Meter mit Zonen grün/orange/rot und violetter Ziel-Markierung | ✅ |
| `TipCard` | Problem → Aktion → *Why*, linke Kante in Severity-Farbe | ✅ |
| `FeedbackAlert` | Großer, statischer Alarm unten (kein Pulsieren) | ✅ |
| `Metric` | Kennzahl-Kachel (Mono-Wert + Einheit) | ✅ |
| `SpectrumView` | Spektrum, log. Frequenzachse 20 Hz–20 kHz | ⏳ |
| `MaskingHeatmap` | Instrument × Band | ⏳ |
| `ChannelStrip` | Gain/HPF/EQ/Comp, Diff aktuell → Vorschlag | ⏳ |
| `ConsoleConnector` | Pult wählen, IP, Verbindung testen, „Allow writes“ | 🟡 (UI-Gerüst) |
| `BandLineupBuilder` | Besetzung für Modul 5 | ⏳ |
| `ResponsePlot` | Frequenzgang/Phase/GD, Log-Achse, ±3-dB-Band, Blanking-Lücken, Cursor | ✅ |
| `RoomTuningView` | Modul 6: Measure, Equalize, Room acoustics, Sub alignment | ✅ |
| `GeqBars` | 31-Band-GEQ-Anzeige | ✅ |

### 5.8 Sprache (wichtig!)
**Die sichtbare UI ist komplett Englisch** (Design-Art 12), auch alle Tipp-Texte, die das Backend liefert. Interne Doku wie diese Datei darf Deutsch sein. Code, Dateinamen und Tests sind Englisch. Der Ton ist kurz, ruhig und konkret, z. B. `Feedback at 2512 Hz. Suggested notch −4 dB.` statt `FFT peak detector triggered`.

### 5.9 Was Worship Mix bewusst NICHT übernimmt
Setlist-Rail, Nashville- und Key-Anzeigen, Pad-Controls, XY-Pad, Waveform und Stem-Mixer aus Loops. Die Familie entsteht durch Marke, Farbe, Typografie und Ruhe, nicht durch identische Screens.

### 5.10 Qualitätscheck vor Freigabe
Es gilt die Checkliste aus Design-Art.md 14. Zusätzlich für Worship Mix:
- [ ] Feedback-Alarm ist aus zwei Metern lesbar und wird von nichts verdeckt.
- [ ] Kill-Switch ist auf jedem Screen in einem Schritt erreichbar.
- [ ] Alle Backend-Texte sind Englisch.
- [ ] Screenshots bei 1440 px, 1024 px und 390 px geprüft.

---

## 6. Modul 1 – Mix Analyzer & Coach

### Ziel
Ein Mix oder mehrere Stems werden hochgeladen. Die App misst objektiv und übersetzt die Messwerte in **konkrete, umsetzbare Tipps mit Begründung**.

### Features

1. **Upload:** Ein Stereo-Mix **oder** mehrere Stems (mit Instrument-Tag: Lead Vocal, BGV, Kick, Snare, Bass, Keys, AG, EG, Pad ...).
2. **Optional:** Ein Mix ohne Stems wird per **Demucs** in Vocals/Drums/Bass/Other zerlegt, dann wird die Analyse pro Stem möglich.
3. **Metriken:**
   - Integrated LUFS, Short-Term-LUFS-Verlauf, Loudness Range (LRA)
   - Sample Peak, **True Peak** (4× Oversampling)
   - Crest Factor / PLR (Peak-to-Loudness-Ratio)
   - Spektrale Balance in Bändern (siehe 12.2), Vergleich mit Genre-Zielkurve
   - Stereo: Korrelation, Breite, Mono-Kompatibilität, Bass-Mono-Check (< 120 Hz)
   - Phase: Korrelation zwischen Stems (z. B. Kick-In/Kick-Out, Snare Top/Bottom)
   - **Maskierung:** Für jedes Stem-Paar die Energieüberlappung pro Band
   - Clipping, DC-Offset, Stille am Anfang/Ende
   - Sibilanz (4–10 kHz Spitzen im Vocal), Mulm (200–400 Hz Stau)
4. **Coach-Tipps:** Eine Regel-Engine erzeugt Tipps, die optional vom LLM verständlich formuliert werden.
5. **Report:** Kann als PDF/Markdown exportiert werden. Ein Verlauf zeigt, ob Mix v3 besser als v2 ist.

### Tipp-Format (Pflicht)

Texte in `problem`, `action` und `why` sind **Englisch** (UI-Sprache der Suite, Kap. 5.8). Die Regeltabelle unten ist intern auf Deutsch beschrieben.

```json
{
  "id": "masking_kick_bass_60_100",
  "severity": "warning",           // info | warning | critical
  "category": "masking",           // loudness | eq | dynamics | stereo | phase | masking
  "targets": ["kick", "bass"],
  "problem": "Kick and bass overlap heavily between 60 and 100 Hz.",
  "action": "Cut the bass by 3 dB around 70 Hz (Q 1.5), or sidechain the bass from the kick.",
  "why": "Both compete for the same low end, so the mix gets muddy and loses punch.",
  "params": {"eq": [{"freq": 70, "gain_db": -3, "q": 1.5, "type": "bell"}]},
  "confidence": 0.82
}
```

### Beispiel-Regeln (Startset)

| Regel | Bedingung | Tipp |
|---|---|---|
| Zu leise/laut | Integrated LUFS weit weg vom Ziel | Gain/Limiter anpassen |
| True-Peak-Overs | TP > −1 dBTP | Ceiling auf −1 dBTP |
| Überkomprimiert | PLR < 7 dB | Limiter/Comp entschärfen |
| Mulm | Band 200–400 Hz > Ziel + 3 dB | Breiter Cut 250–350 Hz |
| Harsch | Band 2–5 kHz > Ziel + 3 dB | Cut 2.5–4 kHz, Vocal-Präsenz prüfen |
| Kein Air | 10–16 kHz < Ziel − 4 dB | High Shelf +2 dB ab 10 kHz |
| Bass nicht mono | Seitenanteil < 120 Hz hoch | Bass/Kick mono, Stereo-Imager unten schmal |
| Mono-Probleme | Korrelation < 0 über längere Zeit | Phasenprüfung, Stereo-Effekte |
| Maskierung Vocal/Keys | Überlappung 1–4 kHz hoch | Keys bei 2–3 kHz absenken, Vocal hat Vorrang |
| Sibilanz | Vocal 5–9 kHz Spitzen | De-Esser |

### Akzeptanzkriterien
- Ein 5-Minuten-Stereo-WAV wird in < 10 s analysiert (ohne Demucs).
- Jeder Tipp hat `problem`, `action` und `why`.
- Die LUFS-Messung weicht nach ITU-R BS.1770-4 um ≤ 0,1 LU von Referenz-Tools ab.

---

## 7. Modul 2 – Referenz-Mastering-Pipeline

### Ziel
Track plus Referenzsong rein, fertige Master in mehreren Loudness-Varianten raus.

### Pipeline

```
Input-Track ─► Vorprüfung (Clipping? Headroom? Sample-Rate?)
            ─► matchering (EQ-/Loudness-Match an Referenz)
            ─► optionale Kette (pedalboard):
                 HPF 25 Hz → sanfter Glue-Comp → EQ-Feinschliff → Limiter
            ─► Loudness-Normalisierung je Ziel
            ─► True-Peak-Check (≤ −1 dBTP)
            ─► Export (WAV 24 bit, MP3 320, FLAC)
            ─► Vorher/Nachher-Report (Modul-1-Analyse beider Versionen)
```

### Loudness-Ziele (Presets)

| Ziel | Integrated LUFS | True Peak |
|---|---|---|
| Spotify (Standard) | −14 LUFS | −1 dBTP |
| Apple Music | −16 LUFS | −1 dBTP |
| YouTube | −14 LUFS | −1 dBTP |
| Livestream (Broadcast, EBU R128) | −23 LUFS | −1 dBTP |
| Worship-Release „laut“ | −9 bis −11 LUFS | −1 dBTP |
| Gottesdienst-Playback / Pausenmusik | −18 LUFS | −1 dBTP |

> Werte sind gängige Richtwerte. Plattformen ändern ihre Normalisierung gelegentlich, daher vor dem Release prüfen.

### Features
- **Batch-Modus:** Ein ganzes Album bzw. eine Setlist mit gemeinsamer Referenz und **einheitlicher Album-Lautheit**.
- **A/B-Player:** Original und Master pegelangeglichen (Loudness-Matched) vergleichen, damit „lauter“ nicht automatisch „besser“ klingt.
- **Referenz-Bibliothek:** Eigene Lieblings-Referenzen (z. B. moderne Worship-Produktionen) speichern.
- **Rechtlicher Hinweis:** Referenzsongs werden nur lokal analysiert, nicht gespeichert oder weitergegeben.

---

## 8. Modul 3 – Virtual Soundcheck Assistant (Ursprungskonzept → umgesetzt in Kap. 11b)

### Ziel
Aus einer Soundcheck-Aufnahme (Multitrack) **pro Kanal** sinnvolle Einstellungen vorschlagen und nach Bestätigung ans Pult senden.

### Ablauf

1. **Kanal-Mapping:** Kanalnummer → Instrument (aus Modul 5 oder manuell).
2. **Aufnahme:** 30–60 s Soundcheck pro Instrument oder Band komplett (USB-Multitrack vom SQ/X32, Dante Virtual Soundcard oder DAW-Export).
3. **Analyse pro Kanal:**
   - **Gain:** Ziel-Peak ca. −18 bis −12 dBFS (Headroom!), dabei pult-spezifische Skalierung beachten.
   - **HPF:** Je nach Instrument (siehe 12.3). Kein Rumpeln und kein Trittschall.
   - **EQ:** Resonanzen finden (schmale Spitzen im Spektrum), instrumententypische Korrekturen.
   - **Dynamik:** Crest Factor, Threshold-Vorschlag für Kompressor und Gate (z. B. Toms).
   - **Übersprechen:** Bleed-Erkennung (Becken im Vocal-Mic → HPF höher oder Gate).
4. **Vorschläge anzeigen:** Als `ChannelStrip` mit Diff (aktuell → vorgeschlagen).
5. **Anwenden:** Pro Kanal oder alle. Vorher wird ein **Snapshot** des aktuellen Zustands gespeichert (Undo!).
6. **Vor dem Gottesdienst:** Den Zustand als Szene speichern.

### Wichtig
- **Gain nie automatisch live während des Gottesdienstes ändern.** Das geht nur im Soundcheck-Modus.
- Werte werden im Adapter auf **pultspezifische Bereiche** gemappt (z. B. EQ-Frequenzraster, Q-Bereiche).

---

## 9. Modul 4 – Feedback- & Pegel-Wächter

### Ziel
Echtzeit-Überwachung mit Warnungen auf Tablet oder Handy. Optional greift er automatisch und in engen Grenzen ein.

### Feedback-Erkennung (Algorithmus)
Rückkopplung lässt sich an diesen Merkmalen erkennen:

1. **Schmale, dominante Spitze** im Spektrum (Peak-to-Average-Ratio hoch, z. B. > 15 dB über Nachbarn).
2. **Stabile Frequenz** über mehrere Frames (≥ 200–300 ms).
3. **Wachsende Amplitude** (positive Steigung).
4. **Geringer harmonischer Kontext**, also kein Teil eines Akkords oder Tons (Abgrenzung von gehaltenen Gesangs- und Keyboard-Tönen!).

Umsetzung:

- FFT mit 8192–16384 Punkten bei 48 kHz (Auflösung ≈ 3–6 Hz) und 50–75 % Overlap.
- Quadratische Interpolation des Peaks für genaue Frequenz.
- Kandidaten-Tracking über Frames. Ein Alarm kommt, wenn alle Kriterien erfüllt sind.
- **Ring-out-Modus** (vor dem Gottesdienst): System bewusst an die Feedback-Grenze bringen, Frequenzen sammeln und Notch-Vorschläge machen.

### Aktionen
| Stufe | Aktion |
|---|---|
| 1 – Hinweis | Gelbe Markierung, Frequenz anzeigen |
| 2 – Warnung | Roter Alarm + Push aufs Handy + Vibration |
| 3 – Auto (opt-in) | Schmaler Notch (Q 8–15, −3 bis −6 dB) im Pult-PEQ bzw. GEQ des betroffenen Busses. Maximal N Filter, wird geloggt, Undo möglich |

### Pegel-Wächter
- Master-LUFS (Short-Term) für **Lautstärke im Saal**. Optional gibt es ein SPL-Messmikro mit Kalibrierung und Grenzwerte, z. B. 85–95 dB(A) als Richtwert für Gemeinden.
- Clipping auf Kanälen, Livestream-Bus-Lautheit (−23 / −16 LUFS).
- **Vocal-Verständlichkeit:** Prüft, ob der Lead-Vocal im Mix ausreichend über der Band liegt. Dafür wird die Vocal-Energie im Bereich 1–4 kHz im Verhältnis zum Gesamtmix gemessen.

---

## 10. Modul 5 – KI-Szenen- & Preset-Bibliothek

### Ziel
Aus einer Beschreibung wird eine fertige Startszene.

**Beispiel-Input:**
> „Sonntag, 2 Lead Vocals (m/w), 2 BGV, Akustikgitarre DI, E-Gitarre Kemper, Keys stereo, Pad stereo, Drums 7 Mics, Bass DI, Pastor Headset, 2 Funk-Handhelds. Kleiner Saal, 150 Leute, Livestream.“

**Output:**
1. **Kanalliste** (Patch): Kanal, Name, Farbe, Quelle, Stagebox-Input, Phantom ja/nein.
2. **Presets pro Kanal:** HPF, EQ, Comp, Gate (aus Preset-Bibliothek, Kap. 12.3).
3. **Bus-Struktur:** Monitore/IEMs, FX-Busse (Vocal-Hall, Delay), Livestream-Bus, DCAs bzw. VCAs (Vocals, Band, Drums, Speech).
4. **Export:**
   - direkt per Adapter ans Pult (Namen, Farben, Presets),
   - als PDF/CSV-Kanalliste für die Bühne,
   - als `.json` zur späteren Wiederverwendung.

### Umsetzung
- Das **LLM** wandelt Freitext in strukturiertes `LineupSpec` (JSON, Schema-validiert) um.
- Eine **deterministische Engine** macht aus `LineupSpec` und der Preset-Bibliothek eine `Scene`. Das LLM erfindet keine EQ-Werte frei!
- Preset-Bibliothek als YAML in `presets/` ist versioniert und von Menschen editierbar.
- „Community-Presets“ (später): Teams teilen Presets, z. B. „Shure SM58 Male Worship Lead“.

---

## 11. Console-Adapter (Pult-Unabhängigkeit)

### Interface (Python)

```python
class ConsoleAdapter(ABC):
    name: str
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def get_channel_count(self) -> int
    async def set_fader(self, ch: int, db: float, bus: str = "LR") -> None
    async def set_mute(self, ch: int, muted: bool) -> None
    async def set_gain(self, ch: int, db: float) -> None            # nur Soundcheck-Modus
    async def set_hpf(self, ch: int, freq_hz: float, on: bool = True) -> None
    async def set_peq_band(self, ch: int, band: int, freq_hz: float, gain_db: float, q: float) -> None
    async def set_comp(self, ch: int, threshold_db: float, ratio: float, attack_ms: float, release_ms: float) -> None
    async def set_channel_name(self, ch: int, name: str) -> None
    async def snapshot(self) -> dict                                # aktueller Zustand für Undo
    async def restore(self, snap: dict) -> None
    def capabilities(self) -> set[str]                              # was dieses Pult per Protokoll kann
```

Nicht jedes Protokoll unterstützt alles. Deshalb gibt `capabilities()` an, was geht, und die UI zeigt nur Funktionen an, die verfügbar sind.

### Allen & Heath SQ (SQ-5/6/7, SQ-Rack) – MIDI über TCP

- **Transport:** TCP, **Port 51325**, IP des Pults. Alternativ USB-MIDI oder der MIDI Control App-Treiber.
- **Format:** **NRPN** auf dem eingestellten MIDI-Kanal (Standard 1):
  ```
  Bn 63 MB   (NRPN MSB – Parameter)
  Bn 62 LB   (NRPN LSB – Parameter)
  Bn 06 VC   (Data Entry Coarse)
  Bn 26 VF   (Data Entry Fine)
  ```
  (`n` = MIDI-Kanal − 1)
- Beispiele (laut SQ-MIDI-Protokoll, **unbedingt gegen PDF prüfen**):
  - Mute Input 1: MB `0x00`, LB `0x00`, Wert `00 01` = an / `00 00` = aus
  - Input 1 → LR Level: MB `0x40`, LB `0x00`, Wert = 14-bit Fader-Wert (Tabelle im PDF)
- **Einschränkung:** Das offizielle SQ-MIDI-Protokoll deckt v. a. **Mutes, Fader/Sends, Pan, Szenen-Recall, Soft Keys** ab. **Processing (EQ, HPF, Comp, Gain) ist laut Protokoll nicht oder nur eingeschränkt steuerbar.** Daher:
  - Modul 3 zeigt beim SQ die Werte zum **manuellen Übertragen** an (Schritt-für-Schritt-Anleitung) oder
  - schreibt in eine **SQ-Szene/Library**, wo das möglich ist, oder
  - nutzt Szenen-Recall: vorbereitete Szenen am Pult werden per MIDI abgerufen.
- **Referenz:** *SQ MIDI Protocol Issue 5* (Allen & Heath, PDF), siehe Quellen.

### Behringer X32 / Midas M32 – OSC

- **Transport:** UDP, **Port 10023**.
- Beispiele:
  - `/ch/01/mix/fader` float 0.0–1.0
  - `/ch/01/mix/on` int 0/1 (1 = an, also nicht gemutet)
  - `/ch/01/preamp/hpf` (bzw. `/ch/01/preamp/hpon`)
  - `/ch/01/eq/1/f`, `/ch/01/eq/1/g`, `/ch/01/eq/1/q` (normalisierte Floats, siehe X32-OSC-Doku)
  - `/ch/01/config/name` string
  - `/xremote` alle ~9 s senden, damit das Pult Änderungen zurückmeldet
- X32 kann **fast alles** per OSC, ist also ideal als erste Voll-Implementierung.

### Behringer Wing – OSC
- UDP, **Port 2223**. Andere Adressstruktur als X32 (`/ch/1/fdr` usw.), gegen Wing-OSC-Doku prüfen.

### Weitere (später)
- **Yamaha** (TF/QL/CL/DM7): Eigene Protokolle bzw. RCP über TCP, Doku prüfen.
- **Soundcraft Ui**: WebSocket-basiert.
- **Mock-Adapter:** Simuliertes Pult für Entwicklung und Tests, Pflicht!

### Wert-Mapping
Jeder Adapter enthält `to_native()`- und `from_native()`-Funktionen (dB ↔ 0..1-Float bzw. 14-bit-Wert, Hz ↔ Index usw.). Diese Mappings brauchen **Unit-Tests mit Tabellenwerten aus der Herstellerdoku**.

## 11a. Modul 6 – Room Tuning (Einmessen der PA)

> Inspiriert von der Analyse der iOS-App **HouseCurve** (housecurve.com, alle 28 Doku-Seiten gelesen: Handbuch, Usage, Tuning, App Notes, Download). Worship Mix implementiert die Konzepte **eigenständig**, ohne Code, Kurven oder Texte zu übernehmen, und erweitert sie für Live-Sound in Kirchen.

### 11a.1 Recherche: Was HouseCurve macht

| Bereich | HouseCurve (laut Doku) |
|---|---|
| Plattform | Nur iOS. Gratis-Version plus „Tuning Bundle“ (Abo oder lifetime) für EQ, Echtzeit, Mittelung, Phase/GD, Export |
| Messsignal | **„Chirp“ als Zeitreferenz + logarithmischer Sinus-Sweep**. Wird der Chirp nicht in ca. 10 s gehört, bricht die Messung ab |
| Echtzeit | Rosa Rauschen, Live-Ansicht oder Mittelung, **Moving-Mic-Methode** (Mikro symmetrisch durch den Hörbereich bewegen) |
| Plots | Magnitude (Ziel gelb mit **±3-dB-Band**, Messung grün, gespeicherte Messung grau), **Phase** (gewrappt), **Gruppenlaufzeit**. Ziel für Phase/GD ist immer 0 |
| Qualität | **Coherence Blanking:** Bereiche unter einer SNR-Schwelle werden ausgeblendet. Fehler „Low measurement coherence“ |
| Mittelung | **dB-Mittel für Magnitude, Vektor-Mittel für Phase, arithmetisch für Gruppenlaufzeit**. „Remove Delay“ an beim Mitteln, aus beim Zeitabgleich |
| Messplätze | Schreibtisch 3–5, Wohnzimmer 3–7 Positionen, Mikro immer aufs System gerichtet, Linie links → Mitte → rechts |
| Mikrofone | iPhone-/iPad-Mikro (Abfall unter 60 Hz und über 16 kHz, wird kompensiert) oder extern (UMIK-1, iMM-6) mit Kalibrierdatei |
| Zielkurven | Mitgeliefert: B&K, Harman, Car A/B/C. Faustregel: **ca. −1 dB/Oktave**, „flat klingt im Alltag zu hell“. Editor mit max. 20 Punkten, automatischer oder manueller Pegel-Fit |
| EQ-Generator | **PEQ** (Peak + Shelf) oder **FIR** (Mixed Phase, ca. **250 ms Latenz**). Einstellungen: Frequenzbereich, Max Gain, „Allow only cuts“, Max Filters, Max Q (min. 0,5), Shelf-Q 0,5–1,0. Zeigt die vorhergesagte Kurve und den Max Boost (für Headroom) |
| Tuning-Regeln | Unter ca. **300 Hz (Schroeder)** dominiert der Raum: Peaks und breite Dips glätten. Darüber dominiert der Lautsprecher: nur breite Bereiche (≥ 1 Oktave) korrigieren. Über ca. **10 kHz** oft gar nicht. Tiefe Dips, die es nur an einem Platz gibt, nicht boosten. Lieber Ziel absenken als boosten. Arbeiten von tief nach hoch in kleinen Schritten |
| Zeitabgleich | Chirp auf einen Main-Lautsprecher legen (Referenz), Mains allein und Sub allein messen. Phase bei der Crossover-Frequenz angleichen. **1 Wellenlänge bei 100 Hz = 10 ms**, Polarität drehen = ½ Wellenlänge (5 ms) |
| Crossover | Lautsprecher einzeln ohne Crossover messen, dort trennen, wo sich beide gemessen überlappen. Beispiel: 2.1-System, 100–120 Hz |
| Export | Biquad-Koeffizienten (a0 = 1, **a1/a2 mit umgedrehtem Vorzeichen**, miniDSP-kompatibel), PEQ-Text (Volumio/HifiBerry/Equalizer APO), Impulsantwort-WAV (32-bit float mono, 500 ms; PEQ-Peak bei Sample 0, FIR-Peak bei 250 ms), Crestron DM NAX direkt |
| Integrationen | miniDSP (2x4 HD 96 kHz, DDRC-24 48 kHz), Roon (Convolution, im Zweifel 44,1 kHz), Volumio/FusionDSP (= CamillaDSP), Crestron |
| Dateiformate | Kurvendatei: „Frequenz Gain“ pro Zeile, getrennt durch Leerzeichen, Tab oder Komma, aufsteigend, Interpolation 20 Hz–20 kHz (.txt/.frd). Messung: WAV float32, Peak bei 250 ms, 1 s lang |

### 11a.2 Was Worship Mix daraus macht (und besser für Gemeinden)

| Thema | Worship Mix |
|---|---|
| Plattform | Web-App: **jedes Handy, Tablet oder Laptop** als Messgerät, kein Abo |
| Messsignal | Eigener **Down-Chirp** (8 kHz → 500 Hz) + Log-Sweep 20 Hz–20 kHz (5 s) und Layout mit festen Abständen. Der Down-Chirp ist fast orthogonal zum Up-Sweep und wird deshalb nie mit ihm verwechselt |
| Chirp-Erkennung | **Zweistufig, robust für hallige Kirchen:** (1) Testsignal grob über den 5-s-Sweep finden (hoher Verarbeitungsgewinn), (2) Chirp nur in einem Fenster von ±250 ms suchen, erster starker Treffer = Direktschall. Entstanden, weil in einer Simulation mit viel Hall der einstufige Ansatz den Sweep statt des Chirps fand |
| Aufnahme | Browser-Mikro mit **ausgeschalteter Echo-Unterdrückung, Rauschunterdrückung und Auto-Gain** (sonst wäre die Messung wertlos), oder Upload einer Aufnahme (z. B. Messmikro am Pult-Kanal und USB-Recording) |
| Fehlermeldungen | Englisch und konkret: kein Testsignal gehört, Mikro übersteuert, Aufnahme zu kurz, „Low measurement coherence“ |
| Coherence Blanking | SNR pro Frequenz aus der **dekonvolvierten Stille vor dem Chirp**, Standard-Schwelle 10 dB. Außerhalb des sauberen Sweep-Bands immer ausgeblendet |
| Mittelung | Wie oben: dB / Vektor / arithmetisch. Empfehlung **5–8 Sitzplätze** (vorne links/mitte/rechts, Mitte, FOH, hinten, Empore) |
| Zielkurven | Eigene Startkurven: **Flat, Gentle tilt (−1 dB/Okt), Worship warm, Live band, Speech clarity**. Eigene Kurven als Textdatei hochladbar (gleiches Format wie oben, auch für Mikro-Kalibrierung) |
| Auto-EQ | Greedy-Platzierung plus gemeinsame Optimierung (least squares). **Unterhalb Schroeder** 1/6-Oktav-Glättung und schmale Filter, **darüber** 1/1-Oktav-Glättung mit Q ≤ 2. Boosts nie schmaler als ⅓ Oktave (Q ≤ 4,3), **Max Boost** separat (Standard 4 dB, live wegen Feedback und Headroom), Cuts bis 9 dB. Nur Cuts als Option, Shelf mit Q 0,5–1,0, Korrektur nur 30 Hz–12 kHz, nie dort, wo ausgeblendet ist |
| Pult-Ausgabe | **31-Band-GEQ** (ISO-Terzen, 0,5-dB-Schritte) für jedes Pult, PEQ-Schritte für den Main-Bus, **X32-OSC** (`/main/st/eq/1..6`), SQ: Schritt-für-Schritt-Anleitung (Processing ist per MIDI nicht erreichbar) |
| FIR | **Minimalphase** (Cepstrum-Methode), **0 ms Latenz**, live-tauglich. 250 ms wie bei Mixed Phase wären live unbrauchbar |
| Export | miniDSP-Biquads, PEQ-Text (Equalizer-APO-Syntax mit Preamp), CamillaDSP-YAML, FIR-WAV (float32), Pult-Anleitung als Text |
| **Raumakustik (neu)** | **RT60** pro Oktave (Schroeder-Rückwärtsintegration, T20), **C50** (Sprachverständlichkeit: ≥ +3 dB gut, 0…3 mittel, < 0 schlecht), **Schroeder-Frequenz** f = 2000·√(T60/V) aus Raumvolumen. Daraus folgen konkrete Tipps zu Hall-Effekten und Sprache |
| Sub-Abgleich | Phase bei der Crossover-Frequenz aus einer **zeitlich gefensterten IR** (Direktschall + 2,5 Perioden, mind. 20 ms), damit Nachhall die Phase nicht verfälscht. Mehrdeutigkeit um ganze Perioden wird über die gemessene Ankunftszeit aufgelöst. Ausgabe: Delay Mains/Sub, Hinweis auf Polaritätsdrehung, Sub-Pegel |
| Crossover | −6-dB-Punkte von Mains (bezogen auf 200 Hz–2 kHz) und Sub (bezogen auf 40–80 Hz), Vorschlag = geometrisches Mittel |

### 11a.3 Ablauf für den Techniker (im UI)

1. **Setup:** Test-Signal herunterladen und über die PA abspielen (USB-Playback am Pult oder Laptop auf einem Stereo-Kanal). **Alle Raum-EQs vorher aus.** Optional das Raumvolumen eingeben.
2. **Measure:** Platz wählen, „Measure this seat“ tippen, dann Playback starten (die App hört 11 s zu). 5–8 Plätze messen.
3. **Average:** Plätze anhaken und mitteln.
4. **Equalize:** Zielkurve wählen (Gottesdienst: *Worship warm*, Predigt-Szene: *Speech clarity*) und Grenzen setzen. Danach Vorhersage, Fehler vorher und nachher, % im ±3-dB-Band, „Lower main by …“ prüfen.
5. **Export / Pult:** GEQ oder PEQ auf den **Main-Bus** übertragen, nie auf Eingangskanäle. Danach **neu messen** und kontrollieren.
6. **Room acoustics:** RT60 und C50 ablesen und den Hall-Effekt auf den Vocals danach ausrichten.
7. **Sub alignment:** „Remove delay“ aus, Chirp auf einen Main-Lautsprecher legen, Mains und Sub einzeln messen, Delay setzen, neu messen.

### 11a.4 Technische Umsetzung

| Datei | Inhalt |
|---|---|
| `backend/app/tuning/signals.py` | Testsignal-Layout, Down-Chirp, Log-Sweep, Rosa Rauschen |
| `backend/app/tuning/measure.py` | Chirp-Erkennung, regularisierte Dekonvolution, IR-Fenster, Magnitude/Phase/GD auf 480-Punkte-Log-Raster (~1/48 Okt.), SNR/Blanking, Mittelung |
| `backend/app/tuning/targets.py` | Zielkurven, Kurvendatei-Parser, Auto-Fit (200 Hz–2 kHz) |
| `backend/app/tuning/biquad.py` | RBJ-Cookbook: Peak, Low/High Shelf |
| `backend/app/tuning/eq.py` | Auto-PEQ, GEQ-31, Minimalphasen-FIR |
| `backend/app/tuning/acoustics.py` | RT60, C50, Schroeder-Frequenz |
| `backend/app/tuning/alignment.py` | Sub-Zeitabgleich, Crossover-Vorschlag, Pegelabgleich |
| `backend/app/tuning/export.py` | miniDSP, PEQ-Text, CamillaDSP, FIR-WAV, Pult-Plan |
| `backend/app/api/tuning.py` | REST-API (siehe Kap. 16) |
| `frontend/components/tuning/*` | `RoomTuningView` (4 Tabs), `ResponsePlot` (SVG, Log-Achse, Blanking-Lücken, Cursor, Toleranzband) |
| `frontend/lib/recorder.ts` + `public/worklets/capture-processor.js` | Mikrofon-Aufnahme über AudioWorklet |

**Plot-Farben (nur Suite-Tokens):** Ziel und ±3-dB-Band `--wm-violet-bright` (gestrichelt), Messung `--wm-success`, Referenz `--wm-text-faint`, Vorhersage `--wm-blue`, Korrektur `--wm-warning`.

**Tests:** 13 Tests mit simuliertem Raum (Direktschall + exponentieller Nachhall + Raummode). Geprüft werden Chirp-Zeitpunkt (±2 ms), Mode-Erkennung, Fehler bei Stille/Clipping, Ankunftszeit mit separatem Chirp-Lautsprecher, dB-Mittelung, Auto-EQ (Mode-Cut, Fehler halbiert, > 95 % im Band), Limits bei „Cuts only“, GEQ- und FIR-Genauigkeit (±1 dB, Minimalphase), Exportformate, Kurvenparser, RT60 (±15 %), Sub-Delay (±0,5 ms) und der komplette API-Ablauf.

### 11a.5 Offene Punkte (TODO)
- ~~Echtzeit-RTA~~ ✅ (11a.6) · ~~Direkt ans Pult~~ ✅ (11a.7)
- Kurven-Editor mit Drag & Drop (max. 20 Punkte) im UI. Upload per Datei geht bereits.
- Messungen dauerhaft speichern (SQLite) und Vorher/Nachher-Vergleich.
- Mikro-Kalibrierung im UI. Die API `/api/tuning/mic-calibration` existiert schon.
- Testen mit echtem Messmikro in deiner Gemeinde; die Grenzwerte (SNR-Schwelle, Q-Grenzen) danach feinjustieren.

### 11a.6 Echtzeit-Analyse mit Rosa Rauschen (Tab „Real time“)

**Recherche:**
- Ein **RTA** ist eine Einkanal-Messung: Er zeigt nur, was im Signal steckt, ohne Phase und ohne Laufzeit. Üblich sind Terzbänder (1/3 Oktave), Profi-Tools gehen bis 1/48. Die **Mittelung** (Integrationszeit) beruhigt die Anzeige. Rosa Rauschen hat **gleiche Energie pro Oktave**, deshalb bedeutet eine waagrechte RTA-Linie ein lineares System.
- Eine **Transfer-Funktion** (Zweikanal-FFT, wie bei Smaart) vergleicht Messung und Referenz und liefert damit Pegel, Phase und Laufzeit. **Kohärenz** zeigt, ob gerade Störgeräusch, Nachhall oder Reflexionen die Messung verfälschen.
- Bei Tiefbass schwankt der RTA-Wert stark (5 dB und mehr), deshalb ist lange Mittelung nötig.

**Umsetzung:**
- **Periodisches Rosa Rauschen:** Periode 65 536 Samples (1,365 s bei 48 kHz). Jede FFT-Linie hat exakt 1/f-Leistung mit zufälliger Phase. Weil die App die Sequenz genau kennt, misst sie eine **echte Transfer-Funktion ohne Referenzkabel**, auch wenn ein anderes Gerät das Rauschen abspielt.
- **Pro Periode:** Zirkuläre Kreuzkorrelation ergibt die Verzögerung, dann H = Y·X*/|X|², dann wird die Laufzeit herausgerechnet und **vektoriell gemittelt**. Kohärenz γ² = |⟨H⟩|² / ⟨|H|²⟩. Unter 50 % wird ausgeblendet.
- **RTA-Modus:** FFT 8192 mit Hann-Fenster und 50 % Überlappung, Bänder 1/1 bis 1/12 Oktave.
- **Mittelung:** *Fast* 0,125 s, *Slow* 1 s, *Moving mic* = unendlich (kumulativ, zum Herumlaufen).
- **Mikrofon:** Aufnahme per AudioWorklet bei 48 kHz, ohne Sprachverarbeitung. **Auf Handys nur über HTTPS** (`npm run dev:https`).
- **Wiedergabe:** „Play pink noise“ blendet sanft ein (1 s), damit es keinen Knall auf der PA gibt.
- **„Save as measurement“:** Die Transfer-Funktion wird als Messung gespeichert (Kohärenz → SNR) und kann direkt in den Auto-EQ.
- **Validierung:** Rosa Rauschen durch einen simulierten Raum (+6 dB bei 100 Hz, −4 dB Shelf ab 5 kHz) als virtuelles Mikro in Chromium. Die App zeigt beides exakt, mit 99 % Kohärenz nach 8 Perioden.

### 11a.7 EQ direkt ans Pult
- `POST /api/tuning/equalize` liefert zusätzlich `console_changes` (Main-PEQ-Bänder 1–6 plus GEQ).
- „Send PEQ to main“ öffnet die Prüfansicht. **X32:** Werte senden (mit Rampe, Snapshot, Undo). **SQ / ohne Pult:** Abhak-Liste.
- Ablauf im Backend: Vorher wird jeder Zielwert per OSC-Abfrage gelesen (Snapshot), dann werden kontinuierliche Werte (Gain, Threshold, Trim) in 6 Schritten über 0,6 s gefahren und alles im Audit-Log festgehalten. `undo` stellt den Snapshot wieder her, ebenfalls mit Rampe.
- Getestet gegen einen **simulierten X32 im Netzwerk** (UDP-Server, der wie ein X32 antwortet).

---

## 11b. Modul 3 – Instruments (Instrument & Mix Tuning)

> Ersetzt das frühere Konzept „Virtual Soundcheck“ (Kap. 8) und erweitert es um Live-Analyse und Gesamtmix.

### 11b.1 Recherche: Wie man es richtig macht
- **Intelligent Music Production** (Reiss, De Man et al., QMUL): Automatisches Mischen nutzt **Merkmale aus dem Audio** (Lautheit, Spektrum, Maskierung), um Gain, EQ, Dynamik und Panning zu steuern. Kreuzadaptive Verfahren, bei denen ein Kanal die Bearbeitung eines anderen beeinflusst, entschärfen **Maskierung**. In Studien schneidet regelbasiertes Wissen gut ab, wenn es als **Startpunkt** dient und der Mensch entscheidet. Genau so arbeitet Worship Mix.
- **Sidechain in Gemeinden:** Typische Konflikte sind *Gesang vs. Pads*, *Kick vs. Bass* und *Keys vs. Tracks*. Ducking ist der „Platz-machen-Knopf“.
- **Pult-Steuerung:** Das **SQ-MIDI-Protokoll** (Firmware 1.6, TCP-Port 51325) kann nur **Szenen, Soft Keys, Mutes, Pegel, Pan und Routing**, kein Processing. Das **X32/M32** lässt sich per **OSC** (UDP 10023) fast vollständig steuern (Gain/Trim, HPF, 4-Band-EQ, Gate, Kompressor inkl. Key-Source, Main-EQ). Daraus folgt: X32 kann direkt senden, das SQ bekommt eine Abhak-Liste.
- **Audio-Zugang:** Beide Pulte haben **32×32 USB**. Am FOH-Laptop liegen damit alle Kanäle einzeln vor (meist *nach dem Preamp, vor dem Fader*). Deshalb schlägt die App **Start-Faderpositionen** vor, statt die aktuellen Fader zu bewerten.

### 11b.2 Ablauf
1. **Quelle:** Demo-Band (synthetisch, ohne Hardware), Upload (Mehrspur-WAV oder eine Datei pro Kanal) oder Live (USB-Interface, Ringpuffer 8 s, Analyse alle 3 s).
2. **Kanal-Zuordnung:** Name → Instrument (wird automatisch aus dem Namen erkannt) → Pult-Kanal.
3. **Pro Kanal:**
   - Pegelstatistik (Peak, lauter Pegel P95, Rauschboden P10, Crest Factor)
   - Langzeit-Spektrum (Welch) mit Steigung (Tilt) und Abweichungen in Bändern (Mulm, Box, Präsenz, Air, Härte, Rumpeln)
   - Resonanzen nur bei Drums, Percussion und Sprache (bei tonalen Instrumenten sind schmale Spitzen Noten, kein Problem)
   - Schläge und Abklingzeit für Gate und Release
   - Zischlaute (Sibilanz) für den De-Esser
4. **Gesamtmix:**
   - Lautheit relativ zum Lead-Vocal → Start-Fader
   - Maskierung pro Oktavband auf dem ausbalancierten Mix (beide Instrumente aktiv, Pegel innerhalb von 6 dB, Band gehört zum Hauptbereich beider)
   - Sidechain-Regeln
   - Master-Kette
5. **Pult:** Vorschläge werden zu **Changes** (konsolenneutral) und dann zu X32-OSC oder zur SQ-Abhak-Liste.

### 11b.3 Regeln für die Einstellungen
| Einstellung | Regel |
|---|---|
| Gain | Ziel-Peak **−12 dBFS**. Trim = −12 − Peak (±18 dB). Clipping wird immer als kritisch gemeldet. Gain **nur im Soundcheck**, nie im Gottesdienst |
| HPF | Profil-Startwert, angehoben bis 0,8 × (Frequenz, ab der 0,5 % der Energie liegen), begrenzt auf den Profil-Bereich |
| EQ (max. 4) | Resonanz: −2…−6 dB, Q 6. Mulm > +3 dB: breiter Cut (Q 1,2). Box/nasal: −3 dB (Q 1,5). Härte (nur bei tonalen Instrumenten, **nie bei Drums**, sonst geht der Anschlag verloren): −2,5 dB bei 3,2 kHz. Fehlende Präsenz: +2 dB. Fehlende Air (Vocals/Strings): +2 dB Shelf. **Cuts vor Boosts** |
| Gate | Nur, wenn Schlag minus Übersprechen ≥ 10 dB, sonst „Gate aus / Mikro näher“. Threshold = Übersprechen + 0,4 × (Schlag − Übersprechen). Release = gemessene Abklingzeit (60–800 ms). Range, Attack, Hold aus dem Profil |
| Kompressor | Threshold so, dass die Ziel-Gain-Reduction bei lauten Passagen (P95) erreicht wird: T = L95 − GR·R/(R−1). Attack bei hohem Crest Factor langsamer (Punch bleibt). Drum-Release aus der Abklingzeit |
| De-Esser | Spitzenfrequenz im Profilbereich bei > +2 dB über der Steigung, 3–6 dB Reduktion |
| Hall/Delay | Profil-Länge, **bei RT60 > 1,6 s eine Stufe kürzer**. Delay = 1/4-Note aus BPM |
| Fader | Profil-Ziel in LU relativ zum Lead-Vocal (z. B. Kick −5, Bass −5, BGV −6, Keys −8, A-Gitarre −9, Pad −15) |
| Sidechain | Kick → Bass (4:1, 1 ms / 80 ms, ~3 dB), Lead → Keys/Pad/Gitarren (dyn. EQ −3 dB bei 2,5 kHz, alternativ Kompressor 2:1), Sprache → Pad/Tracks/Keys (4:1, 20 / 600 ms, ~8 dB) |
| Master | Bus-Kompressor 2:1, 30/150 ms, 1–2 dB GR. Breiter Master-EQ max. ±2 dB gegen die Zielkurve. Limiter −1 dBTP. Stream-Bus −16 LUFS |

### 11b.4 Instrument-Profile (27)
Lead-Vocal m/w, BGV, Chor, Sprache/Headset, Kick, Snare, Tom 1–3, HiHat, Overheads, Bass, A-Gitarre, E-Gitarre, Keys, Aux Keys, Piano, Orgel, Pad, Violine, Cello, Bläser, Cajon, Percussion, Sample Pad, Tracks.
Jedes Profil enthält HPF-Startwert und Bereich, Grundton-, Mulm-, Box-, Präsenz- und Air-Band, optional LPF, Gate, Kompressor und De-Esser, Hall, Delay, Pan, Ziel-Lautheit, Rolle (für Sidechain und Priorität) sowie Praxis-Tipps. Datei: `backend/app/instruments/profiles.py`.

### 11b.5 Validierung (Demo-Band mit eingebauten Fehlern)
Gefunden werden:
- Snare-Ring 328 Hz (geplant 330), Cut −6 dB, Q 6
- Gate-Threshold zwischen Übersprechen und Schlag
- Kick behält seinen Klick
- Mulm auf Keys und Pad
- De-Esser bei 7,5 kHz
- A-Gitarre +8,5 dB Gain (absichtlich zu leise)
- Hall wird bei RT60 1,8 s kürzer, Delay 500 ms bei 120 BPM
- Kick → Bass Sidechain mit Key-Kanal
- Sprache duckt das Pad um ≥ 6 dB

Alle Punkte sind in `backend/tests/test_instruments.py` als Tests abgesichert.

### 11b.6 Grenzen (ehrlich)
- Regeln sind **Startpunkte**. Echte Mikrofone, Räume und Musiker weichen ab. Nach dem ersten echten Soundcheck sollten die Schwellen nachjustiert werden.
- Die Fader-Vorschläge setzen *Pre-Fader*-USB-Abgriffe voraus.
- Für Live-USB muss das Backend **nativ auf dem Laptop** laufen (PortAudio), nicht in Docker.
- X32-Adressen und -Wertebereiche sind als `TODO(verify)` markiert und müssen vor dem ersten echten Einsatz gegen Maillots OSC-Doku geprüft werden. Erst danach am echten Pult senden.

---

## 12. Audio-Fachwissen (Knowledge Base)

Dieses Kapitel ist das Wissen, auf dem Regeln und Presets aufbauen.

### 12.1 Pegel & Lautheit
- **dBFS:** Digitalpegel, 0 dBFS = Maximum.
- **LUFS:** Wahrgenommene Lautheit nach ITU-R BS.1770 (K-Gewichtung + Gating).
- **True Peak (dBTP):** Peak *zwischen* Samples (Oversampling). Wichtig für Codecs (MP3/AAC), daher mit Ceiling −1 dBTP arbeiten.
- **LRA:** Dynamikumfang des Songs in LU. Worship-Balladen haben mehr LRA als Upbeat-Songs.
- **Gain Staging:** Kanäle sollten Peaks um −18 bis −12 dBFS erreichen. So bleibt Headroom für Plugins und Busse.

### 12.2 Frequenzbänder (Hörbereich)
| Band | Bereich | Charakter |
|---|---|---|
| Sub | 20–60 Hz | Fühlen, Kick-/Bass-Fundament, Rumpeln |
| Bass | 60–250 Hz | Wärme, Fülle |
| Low-Mids | 250–500 Hz | Mulm, „Karton“ |
| Mids | 500 Hz–2 kHz | Körper, „Nasal“ (~1 kHz), Honky |
| High-Mids | 2–5 kHz | Präsenz, Verständlichkeit, Härte |
| Presence | 5–8 kHz | Definition, Sibilanz |
| Air | 8–20 kHz | Glanz, Luft |

### 12.3 Instrumenten-Presets (Startpunkte, nicht Gesetz!)
| Instrument | HPF | Typische EQ-Moves | Dynamik |
|---|---|---|---|
| Lead Vocal (m) | 80–100 Hz | −2…−4 dB @ 250–350 Hz, +2 dB @ 3–5 kHz, Air +2 dB @ 10–12 kHz | Comp 3:1, 3–6 dB GR, De-Esser 5–8 kHz |
| Lead Vocal (w) | 100–150 Hz | −2 dB @ 300–400 Hz, Präsenz 3–5 kHz vorsichtig | Comp 3:1, De-Esser 6–9 kHz |
| BGV | 120–180 Hz | Low-Mids stärker raus, Präsenz weniger als Lead | Comp 4:1 |
| Sprache / Pastor (Headset) | 100–150 Hz | −3 dB @ 200–300 Hz, +2 dB @ 2–4 kHz, Notch für Raumresonanzen | Comp 3:1, schnelle Attack |
| Kick | 30–40 Hz | +3 dB @ 50–70 Hz, −4 dB @ 300–400 Hz, +3 dB @ 3–5 kHz (Beater) | Gate optional |
| Snare | 80–100 Hz | +2 dB @ 180–250 Hz (Body), −2 dB @ 400–800 Hz (Ring), +2 dB @ 5 kHz | Comp 4:1 |
| Toms | 60–80 Hz | −3 dB @ 300–500 Hz, Attack 3–5 kHz | Gate |
| Overheads | 150–300 Hz | Low-Mids raus, Air leicht hoch | – |
| Bass DI | 30–40 Hz | Fundament 60–100 Hz, −2 dB @ 250 Hz, Definition 700 Hz–1 kHz | Comp 4:1 |
| Akustikgitarre DI | 80–120 Hz | −3 dB @ 200–300 Hz (Bauch), +2 dB @ 5 kHz | Comp 3:1 |
| E-Gitarre | 80–100 Hz | Low-Mids Platz für Vocals, LPF 8–10 kHz | – |
| Keys / Piano | 60–100 Hz | Mitten im Vocal-Bereich (1–3 kHz) leicht absenken | – |
| Pad / Synth | 100–200 Hz | Viel Low-Mids raus, Platz schaffen | – |

### 12.4 Mixing-Grundprinzipien
1. **Subtraktiv vor additiv:** Erst Problemfrequenzen absenken, dann boosten.
2. **Jedes Instrument bekommt seinen Platz** im Frequenzbereich (Frequency Slotting).
3. **Vocals führen:** Alles um die Stimme herum bauen.
4. **Kontext statt Solo:** EQ-Entscheidungen im Mix treffen, nicht nur bei Solo-Kanälen.
5. **Low-End in Mono**, Breite kommt aus Mitten und Höhen.
6. **Weniger Hall live**, der Raum hallt schon. Kurze Plates für Vocals, Delays für Tiefe.
7. **Kompression = Kontrolle**, nicht Lautheit.

### 12.5 Mastering-Grundprinzipien
- Kleine Moves (±1–2 dB), breite Q-Werte.
- Referenzen immer pegelangeglichen vergleichen.
- Limiter: maximal 2–4 dB GR für natürliche Ergebnisse.
- Erst Probleme beheben (Resonanzen, Low-End), dann die Klangfarbe.

### 12.6 Live-Sound-Wissen
- **Gain-before-Feedback:** Mic-Abstand, Richtcharakteristik, Monitor-Platzierung (Nierenauslöschung nach hinten, Superniere bei ~125°).
- **Ring-out** der Monitore vor dem Gottesdienst.
- **IEMs** reduzieren Bühnenlautstärke und Feedback deutlich.
- **Raumakustik:** Frühe Reflexionen und lange Nachhallzeit (Kirchenräume!) senken die Sprachverständlichkeit. Deshalb lieber weniger Hall-Effekt und mehr Präsenz.

---

## 13. Worship-spezifisches Wissen

- **Gemeindegesang ist das Ziel:** Der Mix soll zum Mitsingen einladen, nicht wie ein Konzert wirken, das die Gemeinde übertönt.
- **Dynamik im Set:** Ruhige Anbetungsphasen (Pad + Keys + Vocal) bis hin zu vollen Upbeat-Momenten. Das System muss diese Szenen-Wechsel kennen (Modul 5: Song-Snapshots „Ruhig“, „Build“, „Voll“).
- **Typische Sonntags-Besetzung:** Wechselnde Ehrenamtliche, daher Presets pro **Person + Mic** speichern.
- **Pad-Sounds** füllen viel Spektrum, deshalb Low-Mids konsequent ausdünnen.
- **Sprache** (Predigt, Ansagen, Gebet) braucht einen eigenen Szenen-Modus: Musik-FX aus, Sprach-EQ an, ggf. Auto-Mixer für mehrere Sprecher.
- **Mehrsprachige Gemeinden** (z. B. Tamil/Deutsch): Übersetzer-Kanal, ggf. eigener Bus für Übersetzung.
- **Livestream-Mix ≠ Saal-Mix:** Im Saal ist das Schlagzeug akustisch laut, im Stream fehlt es. Deshalb braucht der Stream-Bus einen eigenen Mix (Modul 4 überwacht ihn) und Raum-Mics für das Gemeinde-Gefühl.
- **Musikalische Keys/Tonarten:** Integration mit **worship-keys**. Worship Keys speichert Setlists mit Zod-Schema (`lib/storage/schema.ts`): `Song { id, title, artist?, concertKey (0–11), mode, timeSignature, bpm?, notes? }`, `Setlist { id, name, date?, songs[], activeSongId? }`. Worship Mix kann dieses Format importieren (JSON-Export oder Live-Session) und daraus:
  - Delay-Zeiten per Tempo-Sync berechnen (Viertel = 60000 / BPM ms),
  - pro Song einen Mix-Snapshot zuordnen (Ruhig, Build, Voll),
  - beim Songwechsel in Worship Keys (`select-song`, `next-song`) automatisch die passende Szene vorschlagen. Das Umschalten geschieht nie ungefragt, siehe Kap. 15.

---

## 14. KI-Strategie (Regeln + ML + LLM)

Drei Schichten, von deterministisch bis generativ:

| Schicht | Aufgabe | Beispiel |
|---|---|---|
| **1. DSP + Regel-Engine** | Messen und Regeln anwenden | LUFS, Maskierung, Feedback |
| **2. ML-Modelle** | Erkennen und Separieren | Demucs (Stems), Instrumenten-Klassifikation (z. B. PANNs/YAMNet), später eigene Modelle für EQ-Vorschläge |
| **3. LLM (Claude)** | Verstehen und Erklären | Freitext → LineupSpec, Tipps verständlich formulieren, Fragen beantworten („Warum klingt die Snare so blechern?“) |

**Regeln für das LLM:**
- Das LLM **berechnet keine Audio-Werte**. Es bekommt Messwerte als JSON und formuliert daraus Text.
- Strukturierte Ausgaben werden immer gegen ein **JSON-Schema** validiert.
- Das LLM ist optional. Ohne `ANTHROPIC_API_KEY` werden Template-Texte verwendet.
- Prompts liegen versioniert in `backend/app/prompts/`.

**Zukunft (ML-Training):**
- Eigene Daten sammeln, z. B. Paare aus Rohspur und von Agi korrigierter Version. Daraus kann ein Modell lernen, EQ- und Comp-Parameter vorherzusagen.
- MLOps (MLflow, Triton) können später wie in der AIF-Plattform genutzt werden.

---

## 15. Sicherheit im Live-Betrieb

> **Ein Gottesdienst ist live. Fehler sind öffentlich.** Diese Regeln sind nicht verhandelbar.

1. **Default = Read-only.** Neue Pult-Verbindungen schreiben nichts, bis der Nutzer „Schreiben erlauben“ aktiviert.
2. **Snapshot vor jeder Schreibaktion** + Undo-Button in der UI.
3. **Rate-Limiting:** Max. X Änderungen pro Sekunde an das Pult.
4. **Grenzen für Auto-Aktionen:** z. B. Notch max. −6 dB, max. 6 Auto-Notches, nie Fader > 0 dB, nie Gain live.
5. **Kill-Switch:** Großer Button „KI stoppen“, der alle Automatik sofort deaktiviert.
6. **Audit-Log:** Jede Pult-Änderung wird mit Zeit, Quelle (KI/Mensch), altem und neuem Wert protokolliert.
7. **Verbindungsverlust:** Wenn die App abstürzt, läuft das Pult unverändert weiter. Die App darf nie „Heartbeat-abhängig“ steuern.
8. **Netzwerk:** Pult-Netz idealerweise getrennt vom Gäste-WLAN, App nur im lokalen Netz.

---

## 16. API-Design

```
POST   /api/analyze                 Upload Mix/Stems → job_id
GET    /api/jobs/{id}               Status + Ergebnis (Metriken, Tipps)
POST   /api/separate                Mix → Stems (Demucs) → job_id
POST   /api/master                  Track + Referenz + Ziele → job_id
GET    /api/master/{id}/download    Master-Dateien (zip)

GET    /api/consoles/types          Unterstützte Pulte + Capabilities
POST   /api/consoles/connect        {type, host, port} → session
POST   /api/consoles/{sid}/apply    Liste von Änderungen (mit dry_run)
POST   /api/consoles/{sid}/snapshot
POST   /api/consoles/{sid}/restore

POST   /api/soundcheck              Multitrack + Mapping → Vorschläge
POST   /api/scenes/generate         Freitext → LineupSpec → Scene
GET    /api/presets                 Preset-Bibliothek

WS     /ws/live                     Meter, Spektrum, Feedback-Alerts (JSON-Frames, ~20 fps)
POST   /api/live/start | /stop      Wächter starten/stoppen
POST   /api/live/killswitch

GET    /api/tuning/test-signal.wav  Chirp + Sweep (float32, 48 kHz)
GET    /api/tuning/pink-noise.wav   Rosa Rauschen (RTA)
GET    /api/tuning/targets          Zielkurven (+ POST: eigene Kurve hochladen)
POST   /api/tuning/mic-calibration  Kalibrierdatei setzen/entfernen
POST   /api/tuning/measure          Aufnahme → Messung + Raumakustik
GET    /api/tuning/measurements     Liste (DELETE /measurements/{id})
POST   /api/tuning/average          Messungen mitteln
POST   /api/tuning/equalize         Auto-EQ, GEQ, Vorhersage, Pult-Plan
POST   /api/tuning/export           peq_text | minidsp | camilladsp | fir_wav | console
POST   /api/tuning/align            Sub-Zeitabgleich, Crossover, Pegel
GET    /api/tuning/pink-period.f32  Eine Periode periodisches Rosa Rauschen (Referenz)
POST   /api/tuning/import-response  Echtzeit-Transfer-Funktion als Messung speichern

GET    /api/consoles/kinds          Pult-Typen
POST   /api/consoles/connect        {kind, host} → session (read-only)
POST   /api/consoles/{sid}/writes   ?enabled=true|false
POST   /api/consoles/{sid}/plan     Changes → Schritte / OSC-Nachrichten (Vorschau)
POST   /api/consoles/{sid}/apply    Snapshot → Rampe → Audit (409 wenn read-only)
POST   /api/consoles/{sid}/undo     Letzten Snapshot wiederherstellen
GET    /api/consoles/{sid}/audit    Protokoll

GET    /api/instruments/profiles    27 Instrument-Profile
GET    /api/instruments/devices     Audio-Eingänge (USB vom Pult)
POST   /api/instruments/demo        Demo-Band analysieren
POST   /api/instruments/analyze     Upload (Mehrspur-WAV oder Dateien) + Mapping
POST   /api/instruments/live/start  Live-Analyse starten (GET live/latest, POST live/stop)
```

---

## 17. Datenmodell

```
Project(id, name, created_at)
AudioAsset(id, project_id, path, kind[mix|stem|reference|master], instrument_tag, sr, channels, duration)
Analysis(id, asset_id, metrics_json, tips_json, created_at)
MasterJob(id, input_asset_id, reference_asset_id, targets_json, status, outputs_json)
Console(id, type, host, port, name, write_enabled)
ChangeLog(id, console_id, ts, source[ai|user], param, old_value, new_value)
LineupSpec(id, raw_text, spec_json)
Scene(id, lineup_id, console_type, scene_json)
Preset(id, instrument, mic, person?, params_json, version)
```

---

## 18. Roadmap & Meilensteine

| Phase | Inhalt | Ergebnis |
|---|---|---|
| **M0 – Fundament** ✅ | Repo, Docker, FastAPI-Skeleton, Next.js-Frontend im Suite-Design (Shell, Analyzer-Screen), Mock-Adapter, CI | App startet, Design steht (offen: echtes Logo) |
| **M1 – Analyzer** | Modul 1 komplett (ohne Demucs), Tipp-Engine, Report | Erster echter Nutzen |
| **M2 – Mastering** | Modul 2 inkl. Batch & A/B | Releases mastern |
| **M3 – Stems** | Demucs-Integration, Maskierungsanalyse | Tiefere Analyse |
| **M4 – Pult** ✅ | X32 per OSC (Query, Rampe, Snapshot, Undo, Audit), SQ als Abhak-Liste, Übungs-Pult | Pult-Steuerung |
| **M5 – Instruments** ✅ | Modul 3: Kanal- und Mix-Analyse, Sidechain, Master, Live-USB, Upload, Demo, Senden ans Pult | Live-Unterstützung |
| **M6 – Live-Wächter** | Modul 4 + Push-Alerts | Feedback-Schutz |
| **M7 – Szenen** | Modul 5 + LLM | Sonntags-Vorbereitung in 2 Minuten |
| **M8 – worship-keys-Integration** | Setlist/Tonart/Tempo-Sync | Ökosystem |
| **M9 – Room Tuning** 🟢 | Modul 6 inkl. Echtzeit (RTA + Transfer-Funktion) und Senden ans Pult ✅. Offen: Kurven-Editor, Persistenz | PA klingt in jedem Raum gut |

**Lernpfad für Agi (Junior Dev):** M0 → M1 selbst mitbauen (FFT, LUFS verstehen), dann M4 (Netzwerkprotokolle) und erst danach Echtzeit (M6), weil das am schwierigsten ist.

---

## 19. Coding-Konventionen & Tests

- **Python:** Type Hints überall, `ruff` + `black`, Pydantic-Modelle für alle API-Daten.
- **Struktur:** Ein Paket pro Modul (`analysis/`, `mastering/`, `consoles/`, `live/`, `presets/`).
- **Kein Audio im Repo** außer kurzen, synthetisch generierten Testdateien.
- **Tests mit synthetischen Signalen:**
  - Sinus 1 kHz bei −20 dBFS → bekannter LUFS-Wert
  - Rosa Rauschen → flaches Band-Verhältnis
  - Sinus + wachsender schmaler Peak → Feedback-Detektor muss anschlagen
  - Gehaltener Akkord → Feedback-Detektor darf **nicht** anschlagen
- **Adapter-Tests** gegen Mock-Server (UDP/TCP lokal).
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:` ...).
- **Doku:** Jede neue Regel und jedes Preset steht auch in dieser Datei bzw. in `docs/`.

---

## 20. Glossar

| Begriff | Bedeutung |
|---|---|
| FOH | Front of House – Hauptmischplatz im Saal |
| HPF / LPF | Hochpass- / Tiefpassfilter |
| PEQ / GEQ | Parametrischer / Grafischer EQ |
| GR | Gain Reduction (Kompressor) |
| BGV | Backing Vocals |
| DI | Direct Input (Box) |
| IEM | In-Ear-Monitoring |
| DCA / VCA | Gruppensteuerung ohne Audio-Summierung |
| Stem | Teilspur (z. B. alle Drums) |
| NRPN | Non-Registered Parameter Number (MIDI) |
| OSC | Open Sound Control (Netzwerkprotokoll) |
| Ring-out | Gezieltes Finden von Feedback-Frequenzen vor der Veranstaltung |
| Sweep | Sinuston, der logarithmisch von 20 Hz bis 20 kHz gleitet, das Messsignal |
| Chirp | Sehr kurzer Gleitton als Zeitreferenz (bei Worship Mix abwärts, 8 kHz → 500 Hz) |
| Impulsantwort (IR) | Wie der Raum plus PA auf einen einzelnen „Klick“ reagiert, daraus folgt alles andere |
| Gruppenlaufzeit | Wann welche Frequenz am Mikro ankommt (ms) |
| Coherence Blanking | Ausblenden von Bereichen mit zu wenig Signal-Rausch-Abstand |
| Zielkurve / House Curve | Gewünschte Klangbalance, z. B. leicht mehr Bass als Höhen |
| RT60 | Nachhallzeit: Dauer, bis der Schall um 60 dB abgefallen ist |
| C50 | Verhältnis früher (0–50 ms) zu später Energie, Maß für Sprachverständlichkeit |
| Schroeder-Frequenz | Grenze, unterhalb der Raummoden dominieren: f = 2000·√(RT60/V) |
| Minimalphase-FIR | FIR-Filter ohne zusätzliche Latenz |
| RTA | Echtzeit-Analyzer: Pegel pro Frequenzband |
| Transfer-Funktion | Ausgang ÷ Eingang: wie das System das Signal verändert (Pegel, Phase, Zeit) |
| Kohärenz | 0–100 %: Wie verlässlich die Messung gerade ist |
| Sidechain / Ducking | Ein Kanal steuert den Kompressor eines anderen (z. B. Kick drückt Bass kurz weg) |
| Maskierung | Zwei Instrumente überdecken sich im selben Frequenzbereich |
| Pre-Fader | Abgriff vor dem Fader, die Faderstellung ist darin nicht enthalten |

---

## 21. Quellen & Referenzen

- Allen & Heath – SQ MIDI Protocol (Issue 5): https://www.allen-heath.com/content/uploads/2023/11/SQ-MIDI-Protocol-Issue5.pdf
- Allen & Heath – SQ MIDI and DAW Control: https://support.allen-heath.com/hc/en-gb/articles/45947110744465-SQ-MIDI-and-DAW-Control
- Demucs (Meta): https://github.com/adefossez/demucs
- Matchering: https://github.com/sergree/matchering
- Spotify Pedalboard: https://github.com/spotify/pedalboard
- pyloudnorm: https://github.com/csteinmetz1/pyloudnorm
- librosa: https://librosa.org
- ITU-R BS.1770 (Loudness): https://www.itu.int/rec/R-REC-BS.1770
- EBU R128: https://tech.ebu.ch/publications/r128
- HouseCurve (Analyse für Modul 6): https://housecurve.com · Handbuch https://housecurve.com/help · Tuning https://housecurve.com/docs/tuning/equalization · Dateiformate https://housecurve.com/docs/manual/file_formats
- Allen & Heath SQ MIDI Protocol Firmware V1.6: https://support.allen-heath.com/hc/en-gb/articles/47793519540497-SQ-MIDI-Protocol-Firmware-V1-6
- Rational Acoustics, Measurement 101 (RTA vs. Transfer-Funktion, Kohärenz): https://support.rationalacoustics.com/support/solutions/articles/150000190431-measurement-101-types-of-measurement
- ProSoundWeb, RTA & Rosa Rauschen: https://www.prosoundweb.com/?p=38796
- Reiss/De Man, Intelligent Music Production (Frontiers 2018): https://www.frontiersin.org/articles/10.3389/fdigh.2018.00017/pdf
- Church Sound Crew, Sidechain im Gottesdienst: https://www.skool.com/church-audio-engineers-2670/sidechain-compression-the-secret-sauce-nobody-talks-about-in-church-mixing
- X32 OSC (Patrick-Gilles Maillot): https://www.sites.google.com/site/patrickmaillot/x32
- RBJ Audio EQ Cookbook (Biquads): https://www.w3.org/TR/audio-eq-cookbook/
- Farina, A. (2000): Simultaneous measurement of impulse response and distortion with a swept-sine technique (AES)
- Marktüberblick KI-Mixing/Mastering 2026: https://www.roexaudio.com/blog/best-ai-mixing-and-mastering-services-compared-(2026) · https://mixinggpt.com/blog/best-ai-mixing-plugins-2026
- Design-Vorlage: https://github.com/ahaz6/worship-keys
