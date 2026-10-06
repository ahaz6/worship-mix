# Design-Übernahme von worship-keys

Quelle: https://github.com/ahaz6/worship-keys · verbindliche Art Direction: [Design-Art.md](Design-Art.md)

| Bereich | Von worship-keys übernommen | Neu für Worship Mix |
|---|---|---|
| Stack | Next.js 16, React 19, TS strict, reines CSS, Geist Sans/Mono, Zod, Vitest, ESLint-Config, tsconfig | Rewrite `/api/*` → FastAPI-Backend |
| Farben | alle Tokens 1:1 (Präfix `--wk-` → `--wm-`) | Meter-Zonen aus success/warning/danger |
| Hintergrund | Radiale Lichtfelder + statisches Sternenfeld | – |
| Geometrie/Motion | Radien 9/14/20 px, 170 ms, gleiche Easing-Kurve | – |
| Shell | Drei Bereiche, Rail-Breiten, Breakpoints 1180/820 px | Links Modul-Navigation statt Setlist |
| Brand | `BrandMark`-Aufbau, Wortmarken-Verlauf | `WORSHIP / MIX`, Platzhalter-Logo (TODO echtes Logo) |
| Komponenten | `Status`, `.btn-primary`, `.btn`, `.panel-card`, `.field`, `.slider`, `.modal`, `.label`, `.section-title`, `.hint` | `LevelMeter`, `TipCard`, `FeedbackAlert`, `Metric`, `.nav-item`, `.dropzone`, `.btn.tone-kill` |
| Sprache | UI komplett Englisch | – |

Bewusst **nicht** übernommen: Setlist-Rail, Nashville/Key-Anzeigen, Pad-Controls, XY-Pad.
