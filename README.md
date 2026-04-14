# voxprep

[![Korean](https://img.shields.io/badge/lang-Korean-blue)](README.ko.md)

> A GPT-SoVITS dataset preprocessing CLI with the **missing `review` step** — rebuilt TDD-first to make the `slice → asr → review → prep` loop actually usable from the terminal.

> Built on top of [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) (MIT). voxprep rewrites the preprocessing loop; upstream owns the training and inference.

## Highlights

- **The `review` step GPT-SoVITS doesn't have** — an interactive TUI for auditing ASR transcripts, editing inline, deleting bad chunks with undo, and auto-flagging suspicious lines (empty text, interjections, short noise)
- **A proper CLI loop** — `slice → asr → review → prep` composable from the terminal, no browser required, with sensible defaults instead of WebUI dropdowns
- **Built in ten phases, one at a time** — strict Red-Green-Refactor cycles; every pattern is introduced only when a concrete Force requires it
- **macOS Apple Silicon as the first-class target** — default flags (`--language ko`, `--model-size large-v3-turbo`, CPU for CTranslate2) reflect the environment I actually use, not the reference WebUI defaults
- **AI-assisted, user-typed** — Claude is the tutor; I type every line of `src/voxprep/**` and `tests/**`. Q&A and gotchas are accumulated in [`learnings/`](learnings/) in real time

> **Current status**: Phase 02 in progress. The `version` command works. The `.list` parser is at scenario D of 7 (Value Object with manual `__eq__`/`__hash__`, custom exception). The rest of the CLI is a contract — see the [roadmap](#roadmap--10-phases) for what's coming.

---

## Why I Built This

GPT-SoVITS has everything you need to train a voice synthesis model — except a preprocessing front-end that makes repeated dataset work actually tolerable. The reference code ships with a WebUI and a set of half-independent scripts (`slicer2.py`, `fasterwhisper_asr.py`, `1-get-text.py`), each with its own button, dropdown, and set of assumptions.

Two specific frictions kept showing up in my own use:

1. **The CLI loop is broken.** Running `slice → asr → review → prep` on a batch of files shouldn't require opening a browser. The existing tools require constant tab-switching, don't compose, and the defaults are tuned for the reference configuration — every run starts by re-entering the same flags.
2. **There is no `review` step at all.** Whisper's ASR output lands in a `.list` file (`audio_path|speaker|language|text`) that I'm supposed to edit... how? With `vim`, while scrolling through hundreds of lines and hoping I don't break the `|` delimiter? ASR mistakes that slip through don't surface until training is already under way.

So I'm rebuilding the preprocessing pipeline as a proper CLI, and **writing the `review` step that should have been there** — keyboard-driven, with inline audio playback, inline editing, delete/undo, and automatic flagging of suspicious lines.

Alongside the practical CLI, I'm using the project to embody **TDD Red-Green-Refactor** (Kent Beck) and **Object Design Practices** (Matthias Noback's 46 rules). Every line goes through a failing test first, every pattern has to be justified by a Force before it's introduced, and every non-trivial decision gets recorded in [`learnings/DISCOVERIES.md`](learnings/DISCOVERIES.md) with its rationale.

---

## How I Study

```
1. Read the phase guide (docs/phases/phaseNN-*.md) — scope + learning targets
       ↓
2. Read the GPT-SoVITS reference code the phase rewrites (e.g. tools/slicer2.py)
       ↓
3. Claude provides the RED test snippet; I type it into tests/
       ↓
4. Watch the RED evolution:
   ModuleNotFoundError → ImportError → AttributeError → AssertionError
       ↓
5. Minimum code to GREEN — no premature abstraction; if/else is fine
       ↓
6. REFACTOR gate — test quality, code smells, ODP classification, pattern signal
       ↓
7. Log Q&A in learnings/phaseNN-qa.md; log surprises in learnings/DISCOVERIES.md
       ↓
8. Commit with Tidy First separation — feat: / refactor: / docs: / chore:
```

> **The code is mine; Claude is the tutor.** Every line in `src/voxprep/` and `tests/` is typed by hand. Claude only writes infrastructure and documentation files (`pyproject.toml`, `CLAUDE.md`, `docs/phases/*.md`).

---

## Roadmap — 10 Phases

| # | Phase | Deliverable | First ODP Object Introduced | Status |
|---|-------|-------------|-----------------------------|--------|
| 01 | Bootstrap — Typer + pytest | `voxprep version` | *(none yet — just adapters)* | ✅ |
| 02 | `.list` parser | `ListEntry` + `read/write_list_file` | **Value Object** | 🔄 |
| 03 | `slice` command | `voxprep slice <in> <out>` | **Service** (`Slicer`) | ⏳ |
| 04 | `asr` command | `voxprep asr <dir>` | Service + DI + fake double | ⏳ |
| 05 | `review` — navigation | `voxprep review` (`n`/`b`/`q`) | **Entity** (cursor state) | ⏳ |
| 06 | `review` — audio playback | `Enter` to play | subprocess seam | ⏳ |
| 07 | `review` — inline editing | `e` to edit | prompt_toolkit `default=` | ⏳ |
| 08 | `review` — delete + undo | `d` / `u` | **Command** pattern arrival | ⏳ |
| 09 | `review` — auto-flag | `--auto-prune` mode | rule set cohesion | ⏳ |
| 10 | `prep` pipeline | `voxprep prep <raw>` | Rich Live composition | ⏳ |

Legend: ✅ complete · 🔄 in progress · ⏳ pending

Each phase has a guide in [`docs/phases/`](docs/phases/), Q&A in [`learnings/phaseNN-qa.md`](learnings/), and cross-phase principles in [`learnings/DISCOVERIES.md`](learnings/DISCOVERIES.md).

---

## The `.list` Format

Both the rewrite target (GPT-SoVITS) and voxprep share the same `.list` format, which is how ASR output gets carried into training:

```
audio_path|speaker_name|language|text
```

- 4 fields separated by `|` (pipe in `text` → parse error, both directions)
- UTF-8, newline separated, **no trailing newline** (matches upstream's `"\n".join(...)`)
- Language codes are normalized to **lowercase** at the parser boundary — see the [boundary-normalization principle](learnings/DISCOVERIES.md) for why

The parser is the first Value Object voxprep introduces and the place where the "data is validated at the boundary" principle is first enforced.

---

## Tech Stack

| Area | Technology | Notes |
|------|-----------|-------|
| **Language** | Python 3.12 | Pinned via `.python-version` |
| **CLI** | Typer 0.24 | Subcommand groups, auto `--help` |
| **Terminal output** | Rich 15 | Color, tables, `rich.progress.Progress` for subprocess streaming |
| **Interactive input** | prompt_toolkit 3 | Inline editing with `default=` (Phase 07) |
| **Testing** | pytest 9 + Typer `CliRunner` | Unit + integration (`tmp_path` e2e) |
| **Package mgmt** | [uv](https://github.com/astral-sh/uv) | `uv sync` + `uv.lock`, project mode |
| **Rewrite source** | [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | Read directly from `tools/` and `GPT_SoVITS/prepare_datasets/` |

**Phase 04+ dependencies** (`faster-whisper`, `ctranslate2`, `torch`) will be added via `uv add` when the ASR phase begins. Until then the dependency footprint is intentionally tiny.

---

## Project Structure

Current state — phases 01–02 partial. Future phases will add directories marked with their phase numbers:

```
voxprep/
├── src/voxprep/
│   ├── __init__.py              # __version__ (single source of truth)
│   ├── cli.py                   # Typer app + version command       Phase 01 ✅
│   ├── parsing/                 # .list parser                      Phase 02 🔄
│   │   ├── list_file.py         #   ListEntry Value Object
│   │   └── errors.py            #   MalformedListLineError
│   ├── commands/                #   thin adapters per subcommand    Phase 03+
│   ├── slicing/                 #   slicer2 rewrite                 Phase 03
│   ├── transcription/           #   faster-whisper wrapper          Phase 04
│   ├── review/                  #   interactive TUI                 Phase 05~09
│   └── pipeline/                #   prep all-in-one                 Phase 10
│
├── tests/
│   ├── conftest.py
│   ├── unit/                    # fast in-process tests
│   │   ├── test_version.py
│   │   └── test_list_parser.py
│   └── integration/             # CliRunner + tmp_path e2e          Phase 03+
│
├── docs/                        # Claude-authored — specs & guides
│   ├── README.md                # 10-phase roadmap with status
│   └── phases/
│       ├── phase01-bootstrap.md
│       ├── phase02-list-parser.md
│       └── ... (phase03–10)
│
├── learnings/                   # User-authored — the real output
│   ├── README.md                # Learning map (phase → 2-line summary)
│   ├── phase01-qa.md            # Q&A asked during each phase
│   ├── phase02-qa.md
│   └── DISCOVERIES.md           # Gotchas + design principles (cross-phase)
│
├── CLAUDE.md                    # Tutor-mode contract for Claude
├── .python-version              # 3.12
├── pyproject.toml               # [dependency-groups].dev, [project.scripts]
└── uv.lock                      # Tracked for reproducibility
```

---

## Setup

**Requirements:** [uv](https://docs.astral.sh/uv/). uv will install Python 3.12 for you if needed.

```bash
git clone https://github.com/tomato-data/voxprep.git
cd voxprep
uv sync

# Run tests
uv run pytest tests/ -v

# Run the CLI (only `version` is wired up so far)
uv run voxprep --help
uv run voxprep version
# → 0.0.1
```

Phase 04+ will pull in `faster-whisper` and friends via `uv add`. Until then the install is seconds, not minutes.

---

## Reading Order (if you're here to learn)

The most interesting path through this repo isn't the code yet — the code is in progress. The meaningful path is the **methodology + journey**:

1. Read [`CLAUDE.md`](CLAUDE.md) — the tutor-mode contract, CLI-primary framing, Tidy First rules, and "configuration knobs live in SETUP_GUIDE" policy
2. Read [`docs/README.md`](docs/README.md) — the 10-phase roadmap
3. Read [`docs/phases/phase01-bootstrap.md`](docs/phases/phase01-bootstrap.md) — what a phase guide looks like, including the RED evolution scenario
4. Read [`learnings/phase01-qa.md`](learnings/phase01-qa.md) — real questions from working through Phase 01 (`CliRunner` internals, exit codes as HTTP status analogues, why uv now)
5. Read [`learnings/DISCOVERIES.md`](learnings/DISCOVERIES.md) — cross-phase gotchas and design principles. The Typer traps from Phase 01 and the boundary-normalization principle from Phase 02 both live here
6. Follow along as phases get marked ✅ in the roadmap

The git log is also deliberately readable — every commit is a Tidy First step (`feat:` for behavior, `refactor:` for structure, `docs:` for retrospectives and principles, `chore:` for infrastructure). No mixed commits.

---

## Credits

voxprep is a rewrite of the preprocessing front-end of **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** by [RVC-Boss](https://github.com/RVC-Boss) and contributors, released under the MIT License (Copyright © 2024 RVC-Boss). The file formats, algorithms, and sensible defaults in voxprep trace back to GPT-SoVITS — specifically the slicing logic in `tools/slicer2.py`, the ASR wrapper in `tools/asr/fasterwhisper_asr.py`, and the `.list` consumer in `GPT_SoVITS/prepare_datasets/1-get-text.py`. None of GPT-SoVITS's source is distributed in this repository; it is used only as a reference during development.

If voxprep is useful to you, please star the upstream project too. The training and inference — the hard part — live there. voxprep only cleans up the preprocessing loop in front of it.

---

## References

- **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** — the rewrite target. `tools/slicer2.py`, `tools/asr/fasterwhisper_asr.py`, and `GPT_SoVITS/prepare_datasets/1-get-text.py` are the key files I read alongside each phase guide
- **Object Design Style Guide** — Matthias Noback. 46 rules for services, entities, value objects, methods, architecture, and testing
- **Test Driven Development: By Example** — Kent Beck. Red-Green-Refactor and test-as-spec
- **Tidy First?** — Kent Beck. Separating structural from behavioral changes in commits
- **[Typer](https://typer.tiangolo.com/)**, **[Rich](https://rich.readthedocs.io/)**, **[prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)** — the CLI craft trinity
- **[uv](https://docs.astral.sh/uv/)** — the fast package/project manager that replaced pip + venv + pyenv in one tool

---
