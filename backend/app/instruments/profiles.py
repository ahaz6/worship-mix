"""Instrument profiles for worship bands - the knowledge behind Instrument Tuning.

Every value is a *starting point* that the analyzer confirms or adjusts from the
real signal. Bands are (low Hz, high Hz). `balance_lu` = target loudness relative
to the lead vocal (LU) in a typical contemporary worship mix: the congregation
must hear the melody and the words first.

Sources: common live-sound practice (see WORSHIP_MIX.md ch. 12 & 11b), adjusted
for worship: vocal intelligibility first, moderate stage volume, reverberant rooms.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Gate:
    range_db: float
    attack_ms: float
    hold_ms: float
    release_ms: float


@dataclass(frozen=True)
class Comp:
    ratio: float
    attack_ms: float
    release_ms: float
    target_gr_db: float


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    group: str                                 # vocals | drums | keys | guitars | strings | percussion | playback
    hpf: float
    hpf_range: tuple[float, float]
    fundamental: tuple[float, float]
    mud: tuple[float, float] | None = (200, 500)
    box: tuple[float, float] | None = None
    presence: tuple[float, float] | None = (2000, 5000)
    air: tuple[float, float] | None = (8000, 14000)
    lpf: float | None = None
    gate: Gate | None = None
    comp: Comp | None = None
    deesser: tuple[float, float] | None = None
    reverb: str = "medium"                     # none | short | medium | long
    delay: bool = False
    pan: str = "center"
    balance_lu: float = -8.0
    role: str = ""                             # lead_vocal | kick | bass | speech | pad | keys | tracks ...
    tips: tuple[str, ...] = field(default_factory=tuple)


DRUM_GATE_FAST = Gate(range_db=15, attack_ms=0.5, hold_ms=60, release_ms=120)

PROFILES: dict[str, Profile] = {p.key: p for p in [
    # ---------------------------------------------------------------- vocals
    Profile("lead_vocal_m", "Lead vocal (male)", "vocals", 90, (70, 130), (100, 400), (200, 450), (700, 1100),
            (2500, 5000), (9000, 14000), comp=Comp(3.0, 8, 120, 5), deesser=(5000, 8000), reverb="medium",
            delay=True, balance_lu=0, role="lead_vocal",
            tips=("Cardioid dynamic or condenser, 2-5 cm from the mouth.", "Ask the singer to keep the mic close on soft parts.")),
    Profile("lead_vocal_f", "Lead vocal (female)", "vocals", 120, (90, 170), (180, 700), (250, 500), (800, 1200),
            (3000, 6000), (10000, 15000), comp=Comp(3.0, 8, 120, 5), deesser=(6000, 9000), reverb="medium",
            delay=True, balance_lu=0, role="lead_vocal"),
    Profile("bgv", "Backing vocal", "vocals", 140, (100, 200), (120, 700), (200, 500), (700, 1100), (2500, 5000),
            (9000, 14000), comp=Comp(4.0, 10, 120, 6), deesser=(5500, 8500), reverb="medium", pan="spread L/R",
            balance_lu=-6, role="bgv", tips=("Group all BGVs on one DCA/VCA.",)),
    Profile("choir", "Choir (area mic)", "vocals", 150, (120, 220), (130, 900), (200, 500), None, (2000, 5000),
            (8000, 12000), comp=Comp(2.0, 20, 200, 3), reverb="short", balance_lu=-6, role="bgv",
            tips=("Choir mics feed back easily: keep monitors out of their pickup.",)),
    Profile("speech", "Speech / pastor (headset)", "vocals", 120, (100, 180), (100, 400), (180, 400), None,
            (2000, 4500), (8000, 12000), lpf=12000, comp=Comp(3.0, 5, 150, 6), deesser=(5000, 8000),
            reverb="none", balance_lu=0, role="speech",
            tips=("No reverb on speech.", "Headset: notch room resonances before raising gain.")),
    # ----------------------------------------------------------------- drums
    Profile("kick", "Kick drum", "drums", 35, (25, 50), (45, 90), (200, 450), None, (2500, 5000), None,
            gate=Gate(20, 0.5, 40, 150), comp=Comp(4.0, 15, 80, 4), reverb="none", balance_lu=-5, role="kick",
            tips=("Mic inside near the beater for click, outside for body.",)),
    Profile("snare", "Snare drum", "drums", 90, (70, 130), (150, 250), (350, 600), None, (3000, 6000),
            (8000, 12000), gate=Gate(12, 0.5, 60, 150), comp=Comp(4.0, 10, 100, 4), reverb="short",
            balance_lu=-6, role="snare", tips=("Tame ring with a gel pad first, EQ second.",)),
    Profile("tom1", "Tom 1 (high)", "drums", 80, (60, 120), (120, 250), (300, 600), None, (3000, 6000), None,
            gate=Gate(18, 0.5, 120, 250), comp=Comp(4.0, 15, 150, 3), reverb="short", pan="slightly right",
            balance_lu=-8, role="tom"),
    Profile("tom2", "Tom 2 (mid)", "drums", 70, (50, 110), (90, 200), (300, 600), None, (3000, 6000), None,
            gate=Gate(18, 0.5, 140, 300), comp=Comp(4.0, 15, 150, 3), reverb="short", pan="slightly left",
            balance_lu=-8, role="tom"),
    Profile("tom3", "Tom 3 (floor)", "drums", 50, (40, 90), (70, 160), (300, 600), None, (3000, 6000), None,
            gate=Gate(18, 0.5, 180, 400), comp=Comp(4.0, 15, 150, 3), reverb="short", pan="left",
            balance_lu=-8, role="tom"),
    Profile("hihat", "Hi-hat", "drums", 300, (200, 500), (300, 1000), None, None, (3000, 8000), (9000, 15000),
            reverb="none", pan="slightly right", balance_lu=-14, role="hihat",
            tips=("Often overheads are enough - keep the hi-hat channel low.",)),
    Profile("overheads", "Overheads", "drums", 200, (120, 350), (200, 800), (300, 600), None, (3000, 6000),
            (10000, 16000), reverb="short", pan="stereo L/R", balance_lu=-12, role="overheads",
            tips=("In small rooms overheads may only need to fill in cymbals.",)),
    # ------------------------------------------------------------------ bass
    Profile("bass", "Bass guitar (DI)", "guitars", 35, (25, 50), (40, 250), (200, 400), None, (700, 2500), None,
            lpf=6000, comp=Comp(4.0, 20, 150, 5), reverb="none", balance_lu=-5, role="bass",
            tips=("Keep the low end mono and centered.",)),
    # --------------------------------------------------------------- guitars
    Profile("acoustic_guitar", "Acoustic guitar (DI/pickup)", "guitars", 100, (80, 140), (100, 400), (180, 350),
            (500, 900), (2500, 5000), (8000, 12000), comp=Comp(3.0, 15, 150, 4), reverb="medium",
            pan="slightly left", balance_lu=-9, role="acoustic",
            tips=("Pickups sound 'quacky' around 1 kHz - cut gently if needed.",)),
    Profile("electric_guitar", "Electric guitar", "guitars", 90, (70, 130), (100, 1200), (200, 400), (400, 800),
            (2000, 4000), None, lpf=9000, reverb="medium", delay=True, pan="right", balance_lu=-9, role="egtr",
            tips=("Modelers often already add reverb/delay - check before adding more.",)),
    # ------------------------------------------------------------------ keys
    Profile("keys", "Keyboard (main)", "keys", 60, (40, 100), (60, 2000), (200, 500), None, (2000, 4000),
            (8000, 14000), reverb="short", pan="stereo", balance_lu=-8, role="keys",
            tips=("Ask the keyboarder for a fixed output level - no volume pedal surprises.",)),
    Profile("aux_keys", "Aux keyboard / synth", "keys", 100, (60, 200), (100, 3000), (200, 500), None,
            (2000, 4000), (8000, 14000), reverb="short", pan="stereo", balance_lu=-11, role="keys"),
    Profile("piano", "Piano", "keys", 50, (40, 90), (50, 3000), (200, 500), None, (2000, 5000), (8000, 14000),
            comp=Comp(2.0, 20, 200, 2), reverb="short", pan="stereo", balance_lu=-8, role="keys"),
    Profile("organ", "Organ", "keys", 50, (30, 90), (50, 2000), (200, 500), None, (2000, 4000), None,
            reverb="short", pan="stereo", balance_lu=-11, role="keys"),
    Profile("pad", "Pad / ambient synth", "keys", 150, (100, 250), (150, 2000), (200, 500), None, (1500, 4000),
            None, reverb="none", pan="stereo", balance_lu=-15, role="pad",
            tips=("Pads fill everything: thin out the low mids so vocals stay clear.",)),
    # --------------------------------------------------------------- strings
    Profile("violin", "Violin", "strings", 200, (150, 300), (196, 3000), (250, 500), (800, 1200), (2000, 5000),
            (8000, 12000), comp=Comp(2.5, 15, 150, 3), reverb="medium", pan="slightly left", balance_lu=-9,
            role="melody", tips=("Clip-on mics pick up harshness around 2.5-4 kHz.",)),
    Profile("cello", "Cello", "strings", 60, (50, 100), (65, 1000), (200, 400), None, (1500, 3500), None,
            comp=Comp(2.5, 15, 150, 3), reverb="medium", pan="slightly right", balance_lu=-10, role="melody"),
    Profile("brass", "Trumpet / sax", "strings", 120, (90, 180), (150, 1500), (300, 600), None, (2000, 5000),
            (8000, 12000), comp=Comp(3.0, 10, 120, 4), reverb="medium", balance_lu=-9, role="melody"),
    # ------------------------------------------------------------ percussion
    Profile("cajon", "Cajon", "percussion", 50, (40, 80), (60, 150), (250, 500), None, (2500, 6000), None,
            comp=Comp(4.0, 10, 100, 4), reverb="short", balance_lu=-9, role="cajon"),
    Profile("percussion", "Percussion (congas, shaker)", "percussion", 150, (100, 300), (150, 1000),
            (300, 600), None, (3000, 7000), (8000, 14000), comp=Comp(3.0, 10, 100, 3), reverb="short",
            pan="side", balance_lu=-14, role="perc"),
    Profile("sample_pad", "Sample pad (SPD-SX etc.)", "percussion", 40, (30, 80), (40, 3000), (200, 500), None,
            (2000, 5000), (8000, 14000), comp=Comp(3.0, 5, 100, 3), reverb="none", pan="stereo",
            balance_lu=-10, role="samples", tips=("Sample levels vary a lot - ask for a test of every sample.",)),
    Profile("tracks", "Tracks / playback (stereo)", "playback", 40, (30, 80), (40, 8000), (200, 500), None,
            (2000, 5000), (8000, 14000), reverb="none", pan="stereo", balance_lu=-12, role="tracks",
            tips=("Never send the click to FOH.",)),
]}


def get(key: str) -> Profile:
    if key not in PROFILES:
        raise KeyError(f"Unknown instrument '{key}'")
    return PROFILES[key]


def as_dict(p: Profile) -> dict:
    return {"key": p.key, "label": p.label, "group": p.group, "hpf": p.hpf, "balance_lu": p.balance_lu,
            "role": p.role, "has_gate": p.gate is not None, "has_comp": p.comp is not None,
            "tips": list(p.tips)}
