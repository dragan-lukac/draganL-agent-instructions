# SongTabs — audio + lyrics → chords, tabs, ChordPro, Notion

## Context

Dragan writes and records his own songs. Lyrics currently live in the Notion **Songs**
database (`e2813f2c3e06427ca7d06afcee1b00eb`, title property `Naslov`), migrated from
Apple Notes. Notion can hold a "chords" field, but a flat field is not what's wanted —
the goal is **lyrics with chords sitting over the right syllable**, plus **tab blocks for
solos**, all in one document per song.

Today that means transcribing by ear and hand-aligning text. This tool automates the
first draft from a recording, then puts a fast human-in-the-loop review in front of it,
because automatic chord recognition is confidently wrong often enough that unreviewed
output is worse than useless for a songwriter's own catalogue.

**Decisions already made (confirmed with Dragan):**

| Question | Answer |
|---|---|
| Lyrics language | Croatian/Serbian, sometimes mixed with English |
| Audio source | **Multitrack via Focusrite 2i2 on the Mac** — guitar DI and vocal on separate tracks. Phone/room recordings supported as a degraded fallback |
| Review interface | Local web page with waveform + playback |
| Master copy | Local file on disk, one-way sync into Notion |
| Chord display | **Chords above the lyrics**, not inline-embedded — everywhere he reads them |
| Machine | **Apple Silicon Mac, and only that** — recording and running the tool happen on the same box. The ThinkPad is being retired |
| Repo | **New `songtabs` repo**, separate from `draganl-agent-instructions` |

**Intended outcome:** drop the tracks and a lyrics file in, spend ~5 minutes confirming
chords by ear in the browser, get a readable chords-above master file and a formatted
Notion page.

---

## Input contract — tracks have roles

The single most important design consequence of recording through the 2i2: the tool takes
**named tracks, not one file**, and routes each to the analysis it is good for.

```
songtabs new <slug> --guitar guitar.wav --vocals vocal.wav [--mix mix.wav] lyrics.txt
```

| Role | Used for | Required |
|---|---|---|
| `--guitar` | chord recognition, tab transcription, tuning & capo detection | no |
| `--vocals` | forced alignment of lyrics.txt | no |
| `--mix` | playback in the review UI; fallback for any missing role | no |
| `--solo` | isolated solo pass for accurate tabs (added later via `songtabs solo`) | no |

At least one must be given. Missing roles fall back to `--mix`, and a lone phone recording
is simply the case where every role resolves to the same file. This keeps one code path.

### Why this matters

| | Phone in a room | 2i2, separate tracks |
|---|---|---|
| Chord accuracy | ~70%, constant root confusion | ~90%+ |
| Demucs separation | required, 20–40 min/song | **not needed** |
| Solo tabs | rough sketch | genuinely usable |
| Lyrics alignment | fights guitar masking | clean vocal, much tighter |

Three things drive that gap:

1. **A DI has real bass.** Phone mics roll off below ~150 Hz, losing the low-E fundamental
   — which is precisely why C↔Am, G↔Em, F↔Dm get swapped. A DI captures the root, so
   the dominant error mode largely disappears.
2. **No vocal bleed in the chroma.** Sung notes are not chord tones and were the other
   half of the error budget. Separate tracks remove the problem *and* remove the slowest
   stage in the pipeline.
3. **A clean guitar track is the good case for note transcription.** On a room recording
   tabs are a sketch; on a DI they are worth building properly.

### Recording guidance to document in the README

- **Record the dry DI in parallel with any amp sim or distortion.** Distortion adds
  intermodulation harmonics that smear the chroma badly. The tool wants the dry track;
  keep the processed one for listening. If only a distorted track exists, the tool warns
  and falls back to the phone-grade settings.
- **Export stems as WAV, not a stereo bounce.** Three files beat one.
- **No handoff step at all now.** Recording and analysis happen on the same Mac, so the
  tracks never move between machines. This removes the sync dependency the earlier draft
  had to design around.

### Constraints that survive the upgrade

1. **Reverb and ring-out smear chord boundaries.** Snapping chord changes to the detected
   beat/bar grid recovers most of this; free-floating boundaries do not.
2. **Songs repeat.** This is the real leverage: cluster repeated sections, review each
   *unique* section once (~8 bars), propagate to all repeats. Reviewing 200 chord events
   one by one is what makes tools like this unusable, and no amount of input quality
   fixes that.
3. **Recognition is still not transcription.** Even at 90%, voicings, sus/add colour and
   slash-chord inversions need a human ear. The review loop stays the centre of the app.

---

## Architecture

```
guitar.wav   vocal.wav   [mix.wav]   +   lyrics.txt
    │            │           │
    │            │           ▼
    │            │      ┌─ analyse (timing spine, from mix or guitar) ─┐
    │            │      │  load → mono 22.05k → normalise              │
    │            │      │  beats + downbeats + BPM     (librosa)       │
    │            │      │  key estimate                (K-S)           │
    │            │      │  sections + repeat clusters  (self-sim)      │
    │            │      └─────────────────────────────────────────────┘
    │            │           │
    ▼            │           │
 ┌─ chords (guitar track) ─────────────────────────────────┐
 │  tuning + capo detection from open-string partials      │
 │  beat-synchronous CQT chroma                            │
 │  template match over chord vocabulary                   │
 │  Viterbi smoothing w/ key prior                         │
 │  → [bar, beat, chord, confidence, alternatives]         │
 └─────────────────────────────────────────────────────────┘
                 │           │
                 ▼           │
 ┌─ align (vocal track) ──────────────────────────────────┐
 │  forced-align lyrics.txt → per-word → per-line times   │
 └────────────────────────────────────────────────────────┘
                             │
                             ▼
  analysis.json  (cache — every stage is resumable)
        │
        ▼
  ┌─ REVIEW (local web app, http://127.0.0.1:5000) ──────┐
  │  1. Overview   key / BPM / sections on the waveform  │
  │  2. Chords     per-section bar grid, loop & fix      │
  │  3. Lyrics     karaoke view, drag chords onto words  │
  │  4. Tabs       range → transcribe → edit             │
  │  5. Export     preview → save → push to Notion       │
  └──────────────────────────────────────────────────────┘
        │
        ▼
  song.txt  (chords above lyrics — what you read)
  song.pro  (chord anchors — internal, survives edits & transposition)
        │
        └──→ Notion Songs DB page + properties
```

### Two layers: inline anchors, chords-above display

Chords must appear **above** the lyrics — that is the readable format and the one Dragan
wants in front of him. But chords-above is a poor *storage* format: the alignment lives
entirely in whitespace, so one typo in a lyric line shifts every chord above it, and any
transpose or capo change means recomputing every column by hand.

So the tool keeps two layers, and Dragan only ever sees the second:

**Anchor layer — `song.pro` (ChordPro, internal).** Chords bound to a character offset in
the lyric, so they survive lyric edits, transposition and capo changes:

```
{title: Kad padne noć}
{key: Am}
{tempo: 92}
{capo: 2}

{start_of_verse: Strofa 1}
Kad [Am]padne noć i [F]grad utihne
[C]Ja te [G]tražim po [Am]ulicama
{end_of_verse}
```

**Display layer — `song.txt` (what he reads, and what goes to Notion).** Generated from
the anchors, monospace, chords sitting over the syllable they land on:

```
Kad padne noć — Am, 92 bpm, capo 2

[Strofa 1]
    Am              F
Kad padne noć i grad utihne
C      G           Am
Ja te tražim po ulicama

[Solo]
e|-----------------|-------8--10-----|
B|--8--10--8-------|--10-------------|
```

Both files are written on every export. The review UI renders only the display layer.

**The display layer is also readable back in.** `chordpro.py` detects a chord line
(every whitespace-separated token parses as a chord symbol) and maps each token's column
back onto the following lyric line, reconstructing the anchors. That means Dragan can edit
`song.txt` in any editor, or paste a corrected version out of Notion, and re-import it
without losing anything. Where a re-import is ambiguous (a chord column now falls mid-word
after a lyric edit), it snaps to the nearest syllable boundary and flags the line for
review in the UI rather than guessing silently.

Rendering rules that matter in practice:
- Chord sits at the column of its anchor syllable; if two chords would collide or touch,
  the later one is pushed right by one space, and the pair is flagged so the UI can offer
  a bar-grid line instead.
- Chords falling between lyric lines (intros, turnarounds, instrumental bars) render as a
  standalone chord line with bar separators: `| Am | F | C | G |`.
- Long lines are never wrapped — the Notion code block scrolls horizontally, and wrapping
  would break the alignment that is the whole point.

---

## Repo — new, separate from the instructions repo

SongTabs goes in its own repo: `dragan-lukac/songtabs`. It is a real application with
dependencies, a test suite, vendored web assets and a virtualenv — a different lifecycle
from `draganl-agent-instructions`, which is notes, session logs and small standalone
scripts. Keeping them apart also leaves the door open to making SongTabs public later
without untangling personal notes from it.

**Where it lives on the Mac:** `/Users/draganlukac/Documents/Projects/songtabs`, alongside
the already-cloned `draganL-agent-instructions`.

**This session runs in a remote container, not on the Mac.** It cannot write to
`/Users/draganlukac/...`. So the bootstrap is: build and push here, clone there.

1. `create_repository` → `dragan-lukac/songtabs`, private, no auto-init.
2. `add_repo` with push access to pull it into this session, then clone it into the
   container.
3. Scaffold and build on branch `claude/audio-chord-tab-recognition-2qtx3f` (the
   designated branch), push there.
4. **Dragan runs, on the Mac:**
   ```
   cd /Users/draganlukac/Documents/Projects
   git clone git@github.com:dragan-lukac/songtabs.git
   cd songtabs && ./scripts/setup.sh
   ```

**The instructions repo is already cloned there** — good, and it stays a separate repo for
a separate job: `CLAUDE.md`, session logs and the Notion scripts follow Dragan to whatever
machine he works from. Two small additions to it in this session:

- A `Projekti` row pointing at the new `songtabs` repo, matching the existing `circuitQ`
  pattern.
- The `sessions/2026-08-27.md` log.

The broader ThinkPad → Mac migration and the HUB rethink are explicitly **out of scope
here** — Dragan has flagged them as a separate topic. This plan only avoids making them
harder: no new Linux-only assumptions, and the `Key paths` table in `CLAUDE.md` is left
alone rather than half-migrated.

### Layout of `songtabs/`

```
songtabs/                 # the package
  __init__.py
  cli.py                  # songtabs new|analyse|review|solo|export|push
  tracks.py               # track roles, fallback resolution, quality tier detection
  audio.py                # load, normalise, beats, downbeats, BPM, key
  sections.py             # self-similarity → boundaries → cluster repeats
  chords.py               # backend interface + template/Viterbi + tuning/capo detection
  chordino.py             # optional Chordino backend (used if vamp plugin present)
  align.py                # forced alignment (MMS_FA) + beat-grid fallback
  tabs.py                 # note transcription → fretboard solver → ASCII tab
  chordpro.py             # anchors ↔ chords-above rendering, both directions
  notion_sync.py          # push to the Songs DB
  separate.py             # Demucs wrapper, cached — fallback/backfill only
  web/
    app.py                # Flask; serves the review UI, reads/writes analysis.json
    static/               # wavesurfer.js vendored locally, app.js, style.css
    templates/
tests/
scripts/
  setup.sh                # venv + deps + ffmpeg check + optional Chordino
pyproject.toml            # console_script entry point: songtabs
README.md                 # incl. the recording guidance above
CLAUDE.md                 # pointer back to the instructions repo's conventions
.env.example              # NOTION_TOKEN, SONGS_DB_ID — real .env gitignored
```

`pyproject.toml` gives a proper `songtabs` command on `PATH` via the venv, so no launcher
shim is needed — that was only a workaround for the instructions repo's `scripts/` rule,
which no longer applies here.

**Song working directory** — outside the repo. Audio files have no business in git, and
keeping songs out means the repo stays small enough to make public later. The path is
`SONGTABS_ROOT`, defaulting to `~/HUB/Music/songs/`, precisely because the HUB layout is
about to be reconsidered — nothing here should hard-code an assumption Dragan is about to
change. `setup.sh` prompts for it on first run and writes it to `.env`:

```
<slug>/
  tracks/
    guitar.wav        # originals, untouched
    vocal.wav
    mix.wav
    solo.wav          # optional later solo pass
  lyrics.txt          # as written
  analysis.json       # cached analysis + all human corrections
  song.pro            # anchor layer (internal)
  song.txt            # chords-above — the readable master, and what goes to Notion
  meta.yaml           # notion_page_id, language, tuning, capo, track roles, quality tier
```

---

## Implementation

### 0. `tracks.py` — roles and quality tier

- Resolve the role table above: each of `guitar`/`vocals`/`mix`/`solo` maps to a file or
  falls back to `mix`. Every downstream module asks for a *role*, never a filename, so the
  multitrack and phone paths share one code path.
- Verify tracks are the same length and sample rate; if a stem is offset (a late DAW
  export), cross-correlate against the mix and store the offset rather than failing.
- **Detect the quality tier** and record it in `meta.yaml`:
  - `multitrack` — distinct guitar and vocal files.
  - `mix` — one file, decent bandwidth.
  - `phone` — one file with little energy below ~150 Hz, or heavy limiting.
  Also flag a guitar track as `distorted` when its spectral flatness and harmonic density
  are high, and warn that a dry DI would analyse better.
- The tier selects presets downstream: chroma bass weighting, whether Demucs is even
  offered, and how aggressively the review UI pushes low-confidence chords at him.

### 1. `audio.py` — analysis foundation

- Load via `librosa.load` (ffmpeg handles `.m4a` and `.wav`), mono, 22050 Hz.
- Timing spine (beats, key, sections) comes from the `mix` role — the fullest picture of
  the arrangement — falling back to `guitar` when no mix exists.
- Peak-normalise, and light spectral gating (`noisereduce`) only on the `phone` tier —
  a DI needs no denoising, and it is applied to the analysis copy regardless, never to the
  audio served for playback.
- `librosa.beat.beat_track` for BPM + beat frames. Downbeats by picking the beat phase
  that maximises onset-strength periodicity at the bar level (assume 4/4, expose
  `--meter 3` for waltzes).
- Key via Krumhansl-Schmuckler correlation on the mean chroma, returning a ranked list —
  the review UI shows the top 3 so a wrong key guess is one click to fix, and the chord
  prior updates live.

### 2. `sections.py` — the leverage step

- Beat-synchronous chroma + MFCC → recurrence matrix (`librosa.segment.recurrence_matrix`).
- Boundaries via `librosa.segment.agglomerative`, snapped to downbeats.
- Cluster segments by chroma similarity → labels A, B, C… Heuristics propose names
  (longest recurring cluster → "Refren", first cluster → "Strofa"); Dragan renames in the UI.
- Output: unique sections + their repeat instances. **Every chord edit on a section
  propagates to its repeats by default**, with a per-section "this repeat differs" escape.

### 3. `chords.py` — recognition

Runs on the **`guitar` role**, which is the whole point of the multitrack setup: no vocal
bleed, no drums, and a real low-E fundamental. Pluggable backend so quality can improve
without touching the UI.

**Tuning and capo detection (multitrack only).** Before chord decoding, find sustained
open-string ring-outs in the guitar track and fit their partials to a reference pitch.
This yields the actual tuning (A=440 or not, drop-D, half-step-down) and, by looking at
which lowest pitches ever sound, a capo estimate. Both feed the chord vocabulary and the
tab fretboard solver, and both are shown as editable fields in the UI rather than assumed.
Not attempted on the `phone` tier — the bass is not there to measure.

**Default backend (`template`)** — no exotic dependencies, guaranteed to install, and
tunable per quality tier:
- CQT → chroma, averaged per beat (beat-synchronous frames, which handles ring-out smear).
- Chord vocabulary: 12 × {maj, min, 7, maj7, min7, sus4, sus2, dim} plus N (no chord).
- Score each frame against binary chord templates. **Bass/root weighting is set by the
  quality tier**: full weight on a DI, where the root is trustworthy and is the strongest
  disambiguator between a major chord and its relative minor; reduced weight on `phone`,
  where trusting a root that was never captured is what causes the swaps.
- Viterbi over frames: emission = template score, transition = self-transition bonus +
  a key-derived prior (diatonic chords cheap, borrowed chords moderate, out-of-key
  expensive). Chord changes are constrained to beat boundaries, strongly preferring
  downbeats.
- Confidence = margin between best and runner-up score; **alternatives** = next 3
  candidates, with relative major/minor forced into the list on the `phone` tier.

**Optional backend (`chordino`)** — NNLS-Chroma vamp plugin if `scripts/setup.sh`
installed it (Homebrew has `vamp-plugin-sdk`; the NNLS Chroma binary drops into
`~/Library/Audio/Plug-Ins/Vamp`). It was built for clean harmonic input, so on a DI track it is the more
likely winner; selected via `--backend chordino`, and worth benchmarking against
`template` on a real song once both exist.

### 4. `align.py` — lyrics to audio

- Primary: `torchaudio.pipelines.MMS_FA` forced alignment. It takes the known lyrics as
  reference (no need to *recognise* Croatian, only line it up) and romanises via `uroman`,
  which covers Croatian, Serbian (both scripts) and English in one model. ~300M params,
  and on Apple Silicon it runs on the MPS backend — alignment of a 4-minute song is a
  handful of seconds rather than minutes.
- Runs on the **`vocals` role** — an isolated vocal track is the ideal input here, with no
  guitar masking consonants. On the fallback path it uses the Demucs vocals stem if
  `--separate` was run, otherwise the raw mix.
- Fallback (`--align beats`, and automatic if torch is unavailable or alignment
  confidence collapses): vocal-activity detection over the 300–3400 Hz band to find sung
  regions, distribute lyric lines across them proportionally by syllable count. Rough, but
  the UI makes nudging line starts trivial, so it is a usable floor.
- Output: per-word `[start, end, confidence]`, aggregated to per-line.

### 5. `chordpro.py` — the merge and the two layers

**Merge (chords + aligned lyrics → anchors):**
- Walk the chord timeline; for each chord change find the word whose interval contains it.
- Chord lands inside a word → anchor at the nearest syllable boundary (simple vowel-group
  splitter, adequate for both languages).
- Chord falls in a gap between lines → anchor to the following line's start, which renders
  as a standalone chord line.
- Instrumental stretches → a named block with a bar-grid chord line, no lyrics.

**Render (anchors → chords-above):** per the rendering rules above — column placement,
collision push-right, bar-grid lines for instrumentals, no wrapping. Transpose and capo
are applied at render time, so changing capo is a re-render, never a re-edit.

**Parse, both directions:** `song.pro` round-trips trivially; `song.txt` round-trips via
chord-line detection and column-to-offset mapping, with ambiguous re-imports snapped to
the nearest syllable and flagged for review. Hand-editing either file and re-opening the
UI must preserve every correction — this is the property the round-trip tests lock down.

### 6. `tabs.py` — solos

Runs on the **`solo` role if present, otherwise `guitar`** — never the mix when a guitar
track exists. A DI guitar line is the good case for note transcription, which is why this
moves into Phase 1 rather than being deferred.

- Range selected in the UI → `basic-pitch` (Spotify's ONNX model, fast everywhere) → note
  events (pitch, start, duration, confidence).
- Filter to a monophonic line: drop notes below a confidence floor, and where notes
  overlap keep the highest-energy one (leads sit on top). On a dedicated `solo` track this
  filter can be much gentler, since there is nothing else in the signal to reject.
- Fretboard assignment: dynamic programming over candidate (string, fret) positions per
  note, cost = fret distance from the previous position + hand-span penalty + a
  configurable preferred-position bias (open / low / high). Tuning and capo come from the
  detection step in `chords.py`, so drop-D and half-step-down are handled without being
  told.
- Render ASCII tab quantised to the beat grid, with bar lines.
- **Solo pass**: `songtabs solo <slug> solo-take.wav` transcribes an isolated recording of
  just the solo and time-anchors it into the song. Cheap to do through the 2i2 as an
  overdub, and it is the highest-accuracy path — document it as the recommended workflow
  for anything intricate, not an afterthought.

### 7. `web/` — the review UI

Flask, one page per stage, `analysis.json` as the single shared state. Every edit `PATCH`es
that file immediately — no unsaved-work cliff. wavesurfer.js vendored locally.

- **Overview** — waveform with coloured section regions; key/BPM/meter/tuning/capo
  editable inline (pre-filled from detection); changing the key re-runs chord decoding
  against the new prior in place. A track selector switches which role the waveform and
  playback use, so a suspect chord can be checked against the bare guitar rather than the
  mix — the single most useful thing an isolated track buys the review loop.
- **Chords** — bar grid per unique section, one chip per beat. Click a chip → loops that
  bar. Chip shows the confidence as a bar so the eye goes to the weak ones first.
  Keyboard: `space` play/pause, `←/→` move, `1-3` pick an alternative, `m` toggle
  major/minor (the relative-swap fix), `x` mark no-chord, `Enter` free-text.
  A "review low confidence only" filter walks just the uncertain chips in order.
- **Lyrics** — the chords-above view, in monospace, exactly as it will export. Karaoke
  highlight follows playback; drag a chord left/right along the line to move its anchor
  (it snaps to syllable boundaries); drag a line marker to fix alignment drift. Inline
  `[Am]` notation is never shown here.
- **Tabs** — drag a range on the waveform → transcribe → monospace editor with a
  live-validating tab parser; loop playback at 0.5×/0.75× via Web Audio `playbackRate`.
- **Export** — chords-above preview; Save (`song.txt` + `song.pro`); Push to Notion.

### 8. `notion_sync.py`

- Carry the `.env` loading pattern from `scripts/notion.py:24` in the instructions repo
  (`NOTION_TOKEN`, gitignored) — it is ~10 lines and copying it keeps `songtabs` standalone
  rather than coupling two repos. `SONGS_DB_ID` moves into `.env` too, instead of being
  hard-coded the way `scripts/scrape_apple_notes.py:175` does it.
- **Read the Songs DB schema first**, then create only the missing properties
  (`Key`, `BPM`, `Capo`, `Tuning`, `Duration`, `Language`, `Status`) — idempotent, never
  destructive, and it must not assume property names beyond the known `Naslov` title.
- Page body: a callout with key/BPM/capo, then `song.txt` — the chords-above rendering —
  in a **code block**. The code block is non-negotiable here: it is the only Notion block
  that preserves monospace spacing, and chords-above is nothing but monospace spacing. A
  paragraph block would collapse the runs of spaces and destroy the alignment. Tabs go in
  their own code block.
- Existing page → update in place via `meta.yaml:notion_page_id`; otherwise create and
  record the id. Respect the 100-block and 2000-character limits already handled in
  `scripts/scrape_apple_notes.py:180`.
- One-way, local → Notion. Re-running is always safe.

---

## Platform — Apple Silicon

Everything runs on the Mac now, which removes the performance ceiling the earlier drafts
were designing around:

- **`scripts/setup.sh`** creates a venv (Python 3.11+ via Homebrew), installs deps, and
  installs `ffmpeg` if absent. arm64 Homebrew prefix is `/opt/homebrew`; the script
  detects rather than assumes, so it does not break under Rosetta.
- **Torch device selection** is `mps` → `cpu` fallback, resolved once at startup and
  logged. A handful of ops still fall back to CPU on MPS; that is per-op and harmless, but
  the device must be a config value rather than hard-coded so it can be forced to `cpu` if
  an op misbehaves.
- **`basic-pitch`** ships as ONNX/CoreML and is fast either way — no special handling.
- **Demucs stops being a problem.** ~1 minute per song with MPS instead of 20–40. It stays
  out of the default pipeline because multitrack input makes it unnecessary, not because
  it is slow any more — and that makes backfilling the old phone recordings genuinely
  cheap, which is why it earns a place in Phase 3 rather than being written off.

The practical consequence: nothing in this plan needs to be traded away for speed. The
design choices that remain — tracks over stems, review over automation, section clustering
over per-chord confirmation — are about accuracy and Dragan's time, not about hardware.

---

## Phasing

**Phase 0 — handoff (this remote session).** Everything from here on happens on the Mac,
so this session only produces the documents that let the Mac session start cold:

- `docs/songtabs-plan.md` in the instructions repo — this plan, in full. It moves to the
  `songtabs` repo once that exists.
- `sessions/2026-08-27.md` — the session log, which `CLAUDE.md` makes the Mac session read
  on startup.
- Pushed to `claude/audio-chord-tab-recognition-2qtx3f`.

The `songtabs` repo is deliberately **not** created from here — the Mac session creates it,
so the repo is born on the machine that will actually build it.

**Phase 1 — repo scaffold (first Mac session).** Create `dragan-lukac/songtabs`, clone to
`/Users/draganlukac/Documents/Projects/songtabs`, scaffold `pyproject.toml` /
`scripts/setup.sh` / `README.md` / `.env.example` / test harness, move the plan in as
`docs/PLAN.md`. Done when `./scripts/setup.sh` runs clean and `songtabs --help` works.

**Phase 2 — the core loop.** `tracks.py`, `audio.py`, `sections.py`, `chords.py`
(template backend + tuning/capo detection), `align.py`, `chordpro.py`, the
Overview/Chords/Lyrics/Export screens, `notion_sync.py`.
End state: tracks + lyrics → reviewed chords over lyrics → `song.txt` → Notion page.

**Phase 3 — tabs.** `tabs.py`, the solo-pass command, the Tabs screen. Promoted from
"maybe" to a real deliverable by the multitrack input — a DI guitar track makes note
transcription worth shipping.

**Phase 4 — quality and polish.** Chordino backend and a benchmark against `template` on
a real DI track, transpose UI, chord diagrams, batch import of the existing Songs DB
backlog. **Demucs separation lands here, not earlier** — with separate tracks it is only
needed for old phone recordings, so it is a backfill tool rather than part of the pipeline.

Phase 2 is the part that has to be right; the rest builds on a stable `analysis.json`.

---

## Risks

| Risk | Mitigation |
|---|---|
| Recognition still imperfect even on a DI | Section clustering means few decisions; ranked alternatives on one keypress; the review loop is the product |
| Guitar recorded through distortion/amp sim | Tier detection flags it and warns; document recording the dry DI in parallel |
| Old phone-recorded songs in the backlog | Fallback tier keeps them working at lower accuracy; on Apple Silicon Demucs is ~1 min/song, so backfilling them is cheap |
| Stems misaligned on DAW export | Cross-correlate each track against the mix and store the offset instead of failing |
| `torch` + MPS flakiness on some ops | Device is a config value; fall back to CPU per-op, and the beat-grid aligner remains as a no-torch floor |
| HUB layout about to change | Song root is `SONGTABS_ROOT`, not a hard-coded path; nothing to rewrite when the migration happens |
| Notion Songs DB shape unknown | Inspect schema before writing; create missing properties only |

---

## Verification

Steps 1 and 3–7 run on the Mac and cannot be done from the container — the audio hardware,
the recordings and the target platform are all there. Step 2 runs anywhere.

1. **Setup on the Mac** — clone into `/Users/draganlukac/Documents/Projects/`, then
   `./scripts/setup.sh`: creates the venv,
   installs deps, checks for `ffmpeg` (via Homebrew if missing), verifies the `songtabs`
   command resolves, and reports the torch device it selected (`mps` expected). It must
   run clean on a machine that has never had any of this installed — that is the actual
   test, so run it on the real Mac rather than assuming.
2. **Unit tests** (`pytest`), no audio needed:
   - `chordpro.py` round-trips, both layers: anchors → `.pro` → parse → identical
     structure; anchors → chords-above `.txt` → parse → identical anchors. Include cases
     with adjacent chords that collide, chords on the first character of a line,
     standalone instrumental chord lines, and Croatian diacritics (č, ć, š, ž, đ) so
     column arithmetic is verified against multi-byte characters, not just ASCII.
   - Transpose and capo: re-render at a different capo and confirm chord columns still
     sit over the same syllables.
   - Fretboard solver: known note sequence → expected positions; check it does not jump
     the hand across the neck between adjacent notes.
   - Syllable splitter on Croatian and English samples.
   - Chord Viterbi on a synthesised chroma sequence with known chords.
   - `tracks.py` role resolution: every combination of present/absent roles resolves
     without error, and a single-file input maps all roles to that file.
3. **A known-answer recording first.** Before any real song, record a deliberate reference
   through the 2i2: a slow strum of ~10 chords Dragan chooses (include a relative
   major/minor pair, a sus, and a 7th), on a dry DI, at a known tempo and capo. Run it
   through and score chord-for-chord. This is the honest accuracy number, it takes ten
   minutes to make, and it is what tells us whether `template` or `chordino` wins before
   any tuning effort is spent.
4. **End-to-end on a real song** — pick one already in the Songs DB, re-recorded on the 2i2:
   - `songtabs new sloboda --guitar guitar.wav --vocals vocal.wav --mix mix.wav lyrics.txt`
   - `songtabs analyse sloboda` — check reported key/BPM/tuning/capo against playing along
     by ear; the tuning and capo readouts are independently checkable, so verify them first.
   - `songtabs review sloboda` — confirm the browser opens, audio plays, the track selector
     switches sources, and a chip edit survives a page reload (`analysis.json` was written).
   - Verify a section edit propagates to its repeats.
   - Export and diff `song.txt` against the chords Dragan knows are correct — this is the
     real accuracy measure, and worth recording in the session log as a baseline.
   - Hand-edit `song.txt` in a text editor (move a chord, fix a lyric typo), re-open the
     UI, and confirm the edit was read back rather than overwritten.
5. **Notion** — `songtabs push sloboda`, then confirm via
   `python3 scripts/notion.py get-page <id>` that the page has the code block and
   properties; re-run to confirm it updates rather than duplicating.
6. **Fallback path still works** — run one of the old phone recordings through with a
   single file and confirm it degrades gracefully: tier detected as `phone`, no crash on
   missing roles, chords still produced.
7. Re-run the whole pipeline on the same song and confirm cached stages are skipped and
   human corrections in `analysis.json` are preserved.

## Session close

Per CLAUDE.md, write `sessions/2026-08-27.md` in the instructions repo covering what was
built, both repos touched, the measured chord accuracy on the reference recording and the
real song, and what is left for Phase 3. Carry forward the still-open items from
2026-04-18 (Notion Ljudi/Projekti pages, Google Docs sync decision, Apple Notes scraper
re-test) plus the newly raised ThinkPad→Mac migration and HUB rethink.
