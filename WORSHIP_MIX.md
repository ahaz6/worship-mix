# 🎚️ Worship Mix – Vollständige Spezifikation, Wissen & Instruktionen

> **KI-gestütztes Mixing & Mastering für Worship-Teams – egal welches Mischpult.**
> Dieses Dokument ist die *Single Source of Truth* für Menschen und KI-Agenten (Claude Code etc.).
> Wer an Worship Mix arbeitet, liest zuerst diese Datei.

---

## Inhaltsverzeichnis

1. [Vision & Zielgruppe](#1-vision--zielgruppe)
2. [Die 5 Module im Überblick](#2-die-5-module-im-überblick)
3. [Architektur](#3-architektur)
4. [Tech-Stack](#4-tech-stack)
5. [UI-Design: Übernahme von worship-keys](#5-ui-design-übernahme-von-worship-keys)
6. [Modul 1 – Mix Analyzer & Coach](#6-modul-1--mix-analyzer--coach)
7. [Modul 2 – Referenz-Mastering-Pipeline](#7-modul-2--referenz-mastering-pipeline)
8. [Modul 3 – Virtual Soundcheck Assistant](#8-modul-3--virtual-soundcheck-assistant)
9. [Modul 4 – Feedback- & Pegel-Wächter](#9-modul-4--feedback---pegel-wächter)
10. [Modul 5 – KI-Szenen- & Preset-Bibliothek](#10-modul-5--ki-szenen---preset-bibliothek)
11. [Console-Adapter (Pult-Unabhängigkeit)](#11-console-adapter-pult-unabhängigkeit)
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

## 2. Die 5 Module im Überblick

| # | Modul | Kontext | Input | Output | Pult nötig? |
|---|---|---|---|---|---|
| 1 | **Mix Analyzer & Coach** | Studio + Live-Mitschnitt | Mix/Stems (WAV/FLAC/MP3) | Metriken + konkrete Tipps | ❌ |
| 2 | **Referenz-Mastering** | Studio / Release | Track + Referenz | Master-Dateien (mehrere Loudness-Ziele) | ❌ |
| 3 | **Virtual Soundcheck** | Live | Multitrack-Aufnahme (USB/Dante) | Gain/HPF/EQ/Dyn-Vorschläge → Pult | ✅ (optional) |
| 4 | **Feedback- & Pegel-Wächter** | Live (Echtzeit) | Audio-Input (Interface) | Warnungen, optional Auto-Notch | ✅ (optional) |
| 5 | **Szenen- & Preset-Bibliothek** | Vorbereitung | Besetzung in Textform | Startszene, Presets, Kanalliste | ✅ (optional) |

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
│ 01–05            │                                │ Kill-Switch       │
└──────────────────┴────────────────────────────────┴───────────────────┘
  268 px            flexibel, min. 560 px            300 px
```

- **Linke Rail:** Statt der Setlist von Worship Keys steht hier die Modul-Navigation (`01 Mix Analyzer` … `05 Scenes`).
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

## 8. Modul 3 – Virtual Soundcheck Assistant

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
| **M4 – Pult** | X32-Adapter (voll), SQ-Adapter (Mutes/Fader/Szenen), Snapshot/Undo | Pult-Steuerung |
| **M5 – Soundcheck** | Modul 3 | Live-Unterstützung |
| **M6 – Live-Wächter** | Modul 4 + Push-Alerts | Feedback-Schutz |
| **M7 – Szenen** | Modul 5 + LLM | Sonntags-Vorbereitung in 2 Minuten |
| **M8 – worship-keys-Integration** | Setlist/Tonart/Tempo-Sync | Ökosystem |

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
- Marktüberblick KI-Mixing/Mastering 2026: https://www.roexaudio.com/blog/best-ai-mixing-and-mastering-services-compared-(2026) · https://mixinggpt.com/blog/best-ai-mixing-plugins-2026
- Design-Vorlage: https://github.com/ahaz6/worship-keys
