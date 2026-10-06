# 🎚️ Worship Mix

**Dein KI-Co-Pilot für den Gottesdienst-Sound – egal welches Mischpult.**
Raum einmessen, jedes Instrument einstellen, den Gesamtmix prüfen und die Werte ans Pult schicken.

---

## ⚡ So geht's – in 5 Minuten

### 0. Einmal installieren (FOH-Laptop)

Du brauchst **Python 3.11+** und **Node.js 22+**.

```bash
# Terminal 1 – Rechen-Kern
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[live]"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 – Oberfläche
cd frontend
npm install
npm run dev
```

Öffne **http://localhost:3000**. Fertig.

> 📱 **Mit dem Handy messen?** Dann starte die Oberfläche mit `npm run dev:https` und öffne auf dem Handy `https://<IP-des-Laptops>:3000`. Die Zertifikatswarnung einmal bestätigen.
> Warum: Browser geben das Mikrofon nur über HTTPS frei.

---

### 1. Pult verbinden (rechte Spalte → „Console“)

| Dein Pult | Was passiert |
|---|---|
| **Practice console** | Übungs-Pult ohne Hardware. Ideal zum Ausprobieren. |
| **Behringer X32 / Midas M32** | IP eingeben → *Connect*. Werte können **direkt gesendet** werden. |
| **Allen & Heath SQ / SQ-Rack** | IP eingeben → *Connect*. Das SQ erlaubt keine EQ-/Gate-/Kompressor-Steuerung von außen. Du bekommst eine **Schritt-für-Schritt-Liste zum Abhaken**. |

🔒 **Sicherheit:** Am Anfang wird **nur gelesen**. Erst wenn du **„Allow writes“** anhakst, darf die App etwas ändern. Jede Änderung wird vorher gesichert und lässt sich mit **„Undo last send“** zurücknehmen. Werte werden sanft eingeblendet, ohne Knacken.

---

### 2. Raum einmessen (Modul **06 Room Tuning**)

**Schnell, mit Rosa Rauschen (Tab „Real time“):**
1. Alle EQs auf der Summe **ausschalten**.
2. **„Play pink noise“** auf dem Laptop am Pult tippen (oder die Rauschdatei abspielen). Erst leise, dann auf Gottesdienst-Lautstärke.
3. Auf dem Messgerät **„Start listening“** → **„Moving mic“** wählen → 20–30 s langsam durch die Sitzreihen gehen.
4. Steht da **„Clean signal“**, dann **„Save as measurement“** tippen.
5. Tab **„Equalize“** → Zielkurve wählen (*Worship warm* für Musik, *Speech clarity* für die Predigt) → **„Send PEQ to main“**.
6. Nochmal messen und vergleichen. Fertig.

**Genauer, mit Sweep (Tab „Sweep“):** Testsignal abspielen und 5–8 Plätze messen → **„Average“** → weiter wie Schritt 5.
Unter **„Room acoustics“** siehst du außerdem Nachhallzeit und Sprachverständlichkeit, unter **„Sub alignment“** das Delay für den Subwoofer.

---

### 3. Instrumente einstellen (Modul **03 Instruments**)

1. **Audio wählen:**
   - **Try the demo band** – zum Kennenlernen, ohne Hardware.
   - **Upload a soundcheck** – Mehrspur-WAV vom Pult-USB oder eine Datei pro Kanal.
   - **Live from the console** – Pult per USB am Laptop. Die Analyse aktualisiert sich alle 3 s, während die Band spielt.
2. **Kanäle benennen:** Tippe „Kick“, „Snare“, „Bass DI“, „Lead Vox“, „Pastor“ … Das Instrument wird automatisch erkannt.
3. **Ergebnis „Channels“:** Pro Kanal bekommst du **Gain, Low-Cut, EQ, Gate, Kompressor, De-Esser, Hall/Delay, Pan**, jeweils mit Begründung.
4. **Ergebnis „Whole mix“:** Start-Faderpositionen (Lead-Vocal = 0 dB), Frequenz-Konflikte, **Sidechain/Ducking** (Kick → Bass, Gesang → Keys/Pad, Pastor → Pad) und die **Master-Kette** (Bus-Kompressor, Limiter, Livestream).
5. **„Send to console“** pro Kanal oder **„Send all channels to console“**.

💡 *Tipp:* Trage oben die Nachhallzeit aus Room Tuning und das Song-Tempo ein. Dann passt die App Hall-Länge und Delay-Zeiten an.

---

### ❓ Häufige Fragen

| Problem | Lösung |
|---|---|
| „Microphone access is blocked“ | Mikrofon im Browser erlauben. Am Handy `npm run dev:https` nutzen. |
| „Too noisy“ / Lücken in der Kurve | Lauter machen, Ruhe im Raum, Mikro nicht abdecken. |
| „No test signal heard“ | Läuft das Signal wirklich über die PA? Ist der Kanal offen? |
| „No audio input found“ (Live) | Backend direkt auf dem Laptop starten (nicht in Docker) und das Pult-USB-Interface auswählen. |
| SQ: nichts wird gesendet | Richtig so. Das SQ erlaubt das nicht. Nutze die Abhak-Liste. |
| Etwas klingt nach dem Senden schlechter | **„Undo last send“**. Danach mit den Ohren nachjustieren, die App liefert nur den Startpunkt. |

> 🎧 **Goldene Regel:** Worship Mix gibt dir einen sehr guten **Startpunkt**. Das letzte Wort haben deine Ohren, und Lautstärke ist nie automatisch.

---

## Module

| # | Modul | Status |
|---|---|---|
| 1 | Mix Analyzer & Coach | 🟡 Lautheit, True Peak, erste Tipps |
| 2 | Referenz-Mastering | 🟡 Grundgerüst |
| 3 | **Instruments** (Instrument & Mix Tuning) | 🟢 27 Instrument-Profile, Kanal- und Mix-Analyse, Sidechain, Master, Live-USB, Upload, Demo |
| 4 | Live Guard (Feedback) | 🟡 Detektor im Backend |
| 5 | Szenen & Presets | 🟡 Presets |
| 6 | **Room Tuning** | 🟢 Echtzeit-RTA & Transfer-Funktion, Sweep, Auto-EQ, GEQ/FIR/Export, RT60/C50, Sub-Abgleich |
| – | **Send to console** | 🟢 X32/M32 (OSC) · SQ (Abhak-Liste) · Übungs-Pult |

## Für Entwickler

- **[WORSHIP_MIX.md](WORSHIP_MIX.md)** – vollständige Spezifikation, Recherche und Fachwissen
- **[PROMPT.md](PROMPT.md)** – Prompts für Claude Code
- **[CLAUDE.md](CLAUDE.md)** – Regeln für KI-Agenten
- Tests: `cd backend && pytest` · `cd frontend && npm run verify`
- Docker: `docker compose up --build`. **Live-USB-Eingang geht in Docker nicht**, dafür das Backend direkt starten.

## Design
Worship Mix gehört zur **Worship Suite** und nutzt Stack und Design von [worship-keys](https://github.com/ahaz6/worship-keys). Details: [docs/DESIGN.md](docs/DESIGN.md), [docs/Design-Art.md](docs/Design-Art.md).
