# voxprep

[![Korean](https://img.shields.io/badge/lang-Korean-blue)](README.ko.md)

> End-to-end GPT-SoVITS lifecycle as a single CLI — **preprocess → extract → train → infer** — with the **missing interactive `review` step** that upstream never had.

> Built on top of [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) (MIT). voxprep rebuilt the preprocessing loop from scratch with TDD + ODP, then ported the feature-extraction / training / inference stages into the package so the whole lifecycle lives behind `uv run voxprep …`.

## Highlights

- **The `review` step GPT-SoVITS doesn't have** — a keyboard-driven TUI for auditing ASR transcripts: inline audio playback (Enter), inline editing (`e`), delete + undo (`d`/`u`), plus auto-flags for suspicious lines (empty, interjection-only, non-Korean noise, too short, etc.)
- **Reference-audio autoselect for inference** — another gap upstream leaves to manual work. `voxprep infer` scores `.list` candidates by duration (4–8s sweet spot), text length (15–50 chars), and sentence completeness; `--autoselect` picks the best one in place, or an interactive mode shows the top 8 for manual selection. Language is auto-inferred from the `.list` entry too.
- **A single CLI covering the full lifecycle** — `slice → asr → review → prep → extract → train → infer`, all composable from the terminal. No WebUI required for any stage. Every upstream knob is reachable as a `--flag`, and a planned config file ([Phase 20](docs/phases/phase20-config-file.md)) will let you set project-wide defaults once instead of retyping them per run.
- **Sensible, user-validated defaults** — Korean voice data on macOS Apple Silicon as the first-class configuration (`--language ko`, `--model-size large-v3-turbo`, CPU fallback for CTranslate2). The defaults just match what was actually verified end to end.
- **Self-contained** — training and inference aren't subprocess calls into the GPT-SoVITS repo. The relevant modules (`AR/`, `module/`, `TTS_infer_pack/`, `text/`, `eres2net/`) are ported into `src/voxprep/{extract,training,inference}/` so voxprep stands alone. Pretrained weights are the only external artifact.
- **Hand-crafted preprocessing, ported ML core** — Phases 01–10 (preprocessing) were built in strict TDD tutor-mode, one failing test at a time. Phases 13–15 (ML lifecycle) were ported directly from upstream with minimal adaptation, since rewriting a GPT + VITS pipeline from scratch was never the point.

> **Current status**: Phases 01–15 complete. Full pipeline runs end-to-end on macOS. Remaining roadmap: progress UX (Phase 11), `to-wav` utility (12), tkinter GUI (16), MCP/REST server (17), review-loop unification (18), ODP-refinement pass (19), and config-file defaults (20).

For end-to-end usage, see [**`docs/GUIDE.md`**](docs/GUIDE.md). For the object design map, see [**`docs/ARCHITECTURE.md`**](docs/ARCHITECTURE.md).

---

## Why I Built This

GPT-SoVITS has everything to train a voice synthesis model — except a preprocessing front-end that makes repeated dataset work tolerable. The reference code ships a WebUI and a set of half-independent scripts (`slicer2.py`, `fasterwhisper_asr.py`, `1-get-text.py`), each with its own button, dropdown, and set of assumptions.

Two specific frictions kept showing up:

1. **The CLI loop was broken.** Running `slice → asr → review → prep` on a batch shouldn't require opening a browser. The existing tools didn't compose; the defaults were tuned for a reference configuration I didn't match; every run meant re-entering the same flags.
2. **There was no `review` step at all.** Whisper's ASR output lands in a `.list` file (`audio_path|speaker|language|text`) that I'm somehow supposed to edit by hand. With `vim`, scrolling hundreds of lines, trying not to break the `|` delimiter. ASR mistakes that slipped through didn't surface until training was already burning CPU.

So the preprocessing pipeline got rebuilt as a proper CLI with a keyboard-driven review step. Then — because shipping the model end to end matters more than leaving a training stack behind as "upstream's problem" — the downstream stages got ported in too, adapted only where needed to fit voxprep's directory layout and import conventions.

Alongside the practical CLI, this was a vehicle for embodying **TDD Red-Green-Refactor** (Kent Beck), **Tidy First** commit hygiene, and **Object Design Practices** (Matthias Noback's 46 rules). The preprocessing phases were built failing-test-first with every pattern justified only when a concrete Force appeared; the architecture decisions are captured in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and the in-progress ODP refinement plan lives in [`docs/phases/phase19-odp-refinement.md`](docs/phases/phase19-odp-refinement.md).

---

## The Pipeline

```
[video / audio file]
       │  (utils/extract_wav.py — ffmpeg)
       ▼
[raw WAV]
       │
  voxprep prep ──▶  slice → asr → review
       │                            │
       │                            ▼
       ▼                    logs/{exp}/final.list
  chunks/*.wav                      │
                                    ▼
                           voxprep extract ──▶ BERT + HuBERT + speaker-vec + semantic tokens
                                    │
                                    ▼
                           voxprep train {sovits, gpt, all}
                                    │
                                    ▼
                           models/trained/{SoVITS,GPT}_weights_v2Pro/*.{pth,ckpt}
                                    │
                                    ▼
                           voxprep infer ──▶  interactive TTS session
```

Each arrow is a single `uv run voxprep ...` command. Each directory has a documented contract; skip/rerun is automatic where it makes sense.

---

## How the Phases Were Built

Two authorship modes across the project:

**Tutor mode (Phases 01–10)** — preprocessing + review. Every line in `src/voxprep/parsing/`, `slicing/`, `transcription/`, `review/`, `pipeline/` was hand-typed by me with Claude as the RED-cycle tutor: Claude wrote the failing test, I typed it, watched the error evolve (`ModuleNotFoundError → ImportError → AttributeError → AssertionError`), then wrote the minimum production code to GREEN. REFACTOR was a separate commit, classification by ODP, no premature abstraction. Q&A lives in [`learnings/phaseNN-qa.md`](learnings/).

**Port mode (Phases 13–15)** — feature extraction, training, inference. The upstream code for these stages is large, well-understood, and not the point of the exercise. Claude handled the mechanical port: copy files into `src/voxprep/{extract,training,inference}/`, rewrite `from text.X` → `from voxprep.extract.text.X`, wrap the existing entry functions in thin Typer adapters, stitch deps. The boundary is kept clean so the ported code can be isolated or re-pulled from upstream later.

> The preprocessing half is where the ODP and TDD rigor lives. The ported half is pragmatic — reimplementing a VITS decoder was never the goal.

---

## Roadmap

| Part | Phase | Deliverable | Status |
|------|-------|-------------|--------|
| A: Preprocessing (TDD rebuild) | 01 Bootstrap — Typer + pytest | `voxprep version` | ✅ |
|  | 02 `.list` parser (Value Object) | `ListEntry` | ✅ |
|  | 03 `slice` command | `voxprep slice` | ✅ |
|  | 04 `asr` command | `voxprep asr` | ✅ |
|  | 05–09 `review` (nav / play / edit / delete+undo / auto-flag) | `voxprep review [--auto-prune]` | ✅ |
|  | 10 `prep` pipeline | `voxprep prep` | ✅ |
| B: UX + Utility | 11 Progress feedback (Rich Live) | — | ⏳ |
|  | 12 `to-wav` (video → WAV) | `voxprep to-wav` | ⏳ |
|  | 18 Review loop unification (full UI in `--auto-prune`) | — | ⏳ |
| C: Extract + Train (ported) | 13 `extract` | `voxprep extract` | ✅ |
|  | 14 `train {sovits,gpt,all}` | `voxprep train …` | ✅ |
| D: Inference (ported) | 15 `infer` CLI session + ref-audio autoselect | `voxprep infer [--autoselect]` | ✅ |
|  | 16 tkinter GUI | standalone app | ⏳ |
|  | 17 MCP / REST (LLM tool-use) | service | ⏳ |
| E: Refinement | 19 ODP 46-rule refactor | structural | ⏳ |
|  | 20 Config file + CLI override chain | `voxprep config {show,init,edit,path}` | ⏳ |

Legend: ✅ complete · 🔄 in progress · ⏳ pending

Each phase has a guide in [`docs/phases/`](docs/phases/); the hands-on usage manual is [`docs/GUIDE.md`](docs/GUIDE.md); the design map is [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## The `.list` Format

The data contract that ties every stage together:

```
audio_path|speaker_name|language|text
```

- 4 fields separated by `|` (pipe in `text` → parse error, both directions)
- UTF-8, newline separated, **no trailing newline** (matches upstream's `"\n".join(...)`)
- Language codes normalized to **lowercase** at the parser boundary — the [boundary-normalization principle](learnings/DISCOVERIES.md) is documented in learnings

The parser is the first Value Object voxprep introduces and the place where the "validate at the boundary" principle is first enforced.

---

## Tech Stack

| Area | Technology |
|------|-----------|
| **Language** | Python 3.12 (pinned via `.python-version`) |
| **CLI** | Typer 0.24 — subcommand groups, auto `--help` |
| **Terminal** | Rich — color, tables, progress |
| **Interactive input** | prompt_toolkit — inline editing, raw-mode key reads |
| **ASR** | faster-whisper + CTranslate2 (CPU on macOS, CUDA elsewhere) |
| **ML stack** | torch 2.11, torchaudio, transformers ≤ 4.50, pytorch-lightning, peft |
| **Audio** | librosa 0.10, scipy, soundfile, numpy < 2.0, ffmpeg-python |
| **Text processing** | pypinyin, jieba, pyopenjtalk, g2p_en, jamo, ko_pron, g2pk2, python-mecab-ko, ToJyutping |
| **Testing** | pytest 9 + Typer `CliRunner` — 73 tests, unit + integration (`tmp_path` e2e) |
| **Package mgmt** | [uv](https://github.com/astral-sh/uv) (`uv sync`, committed `uv.lock`) |

Roughly 40 direct dependencies after Phase 15; the venv totals ~3 GB once pretrained models are downloaded (another ~2 GB under `models/pretrained/`).

---

## Project Structure

```
voxprep/
├── src/voxprep/
│   ├── cli.py                      # Typer app — registers every subcommand
│   ├── commands/                   # thin CLI adapters, one file per subcommand
│   │   ├── slice.py, asr.py, review.py, prep.py
│   │   ├── extract.py, train.py, infer.py
│   ├── parsing/                    # .list parser (ListEntry VO + errors)
│   ├── slicing/                    # Slicer service + Chunk VO + SliceOptions VO
│   ├── transcription/              # WhisperTranscriber + WhisperLike Protocol + AsrOptions
│   ├── review/                     # ReviewSession Entity + Dispatcher + issues + players
│   ├── pipeline/                   # Workspace VO + slice_step/asr_step/review_step
│   ├── extract/                    # ▼▼ ported ▼▼  BERT/HuBERT/SV/semantic extraction
│   │   ├── text_features.py, hubert_features.py, speaker_vectors.py, semantic_tokens.py
│   │   ├── cnhubert.py, audio_utils.py, hparams.py, models_path.py
│   │   ├── text/                   # upstream text/ — phoneme conversion (28 files, multilingual)
│   │   ├── module/                 # upstream module/ — SoVITS VQ + support (16 files)
│   │   ├── eres2net/               # upstream speaker vector model
│   │   └── configs/                # s1/s2 config templates
│   ├── training/                   # ▼▼ ported ▼▼  SoVITS (s2) + GPT (s1) training
│   │   ├── s2_train.py, s1_train.py, process_ckpt.py, utils.py
│   │   ├── AR/                     # upstream AR/ — GPT model
│   │   ├── config_builder.py       # SovitsTrainOptions / GptTrainOptions VOs
│   │   └── i18n/                   # upstream locale files
│   └── inference/                  # ▼▼ ported ▼▼  TTS inference
│       ├── session.py              # InferenceSession + InferenceInputs VO
│       ├── ref_picker.py           # RefCandidate VO + rank_candidates
│       ├── sv.py, tts_pack/        # upstream TTS_infer_pack
│
├── tests/                          # 73 tests (unit + integration)
│   ├── fixtures/                   # shared doubles (FakeWhisperModel, SpyPlayer, …)
│   ├── unit/                       # in-process
│   └── integration/                # CliRunner + tmp_path e2e
│
├── docs/
│   ├── README.md                   # phase index (roadmap view)
│   ├── GUIDE.md                    # end-to-end user guide (install → infer)
│   ├── ARCHITECTURE.md             # ODP classification map + Mermaid diagrams
│   └── phases/                     # per-phase guides (phase01…phase19)
│
├── learnings/                      # user-authored Q&A + discoveries
│
├── models/                         # (.gitignore) pretrained + trained weights
│   ├── pretrained/                 # chinese-hubert-base, v2Pro, sv, s1v3.ckpt, …
│   └── trained/                    # SoVITS_weights_v2Pro, GPT_weights_v2Pro
│
├── logs/                           # (.gitignore) per-experiment feature-extraction outputs
├── infer_out/                      # (.gitignore) generated WAVs from voxprep infer
│
├── CLAUDE.md                       # tutor-mode contract + project-wide rules
├── .python-version                 # 3.12
├── pyproject.toml
└── uv.lock                         # tracked for reproducibility
```

`models/`, `logs/`, `infer_out/`, and `GPT-SoVITS/` (vendor reference) are all gitignored. Weights are downloaded separately (see [`docs/GUIDE.md`](docs/GUIDE.md) §2).

---

## Setup

**Requirements:** [uv](https://docs.astral.sh/uv/) (will install Python 3.12 for you) and `ffmpeg` on the system PATH.

```bash
git clone https://github.com/tomato-data/voxprep.git
cd voxprep
uv sync                              # ~2 min on first install, pulls torch + transformers + text deps

uv run pytest tests/ -v              # 73 passing
uv run voxprep --help                # full command surface
```

Then drop pretrained weights under `models/pretrained/` per [`docs/GUIDE.md`](docs/GUIDE.md) §2 and you're ready to run the full pipeline.

A minimal end-to-end smoke test (Korean, v2Pro, starting from an MP3/MP4 file):

```bash
python3 utils/extract_wav.py /path/to/source.mp4
mv /path/to/source.wav ~/Desktop/raw_audio/

uv run voxprep prep ~/Desktop/raw_audio \
  --workspace ~/Desktop/datasets/demo --speaker demo \
  --sample-rate 44100 --skip-review

uv run voxprep review ~/Desktop/datasets/demo/final.list          # keyboard-driven cleanup
uv run voxprep extract --list-file ~/Desktop/datasets/demo/final.list \
                       --wav-dir ~/Desktop/datasets/demo/chunks \
                       --exp-name demo_v1

uv run voxprep train all --exp-name demo_v1 \
                         --sovits-epochs 12 --gpt-epochs 20 --save-every 4

uv run voxprep infer --ref-list ~/Desktop/datasets/demo/final.list --autoselect
```

Each command has `--help`; every knob upstream exposes is still reachable.

---

## Reading Order (if you're here to learn)

Two passes through the project, depending on why you're reading.

**"How do I use this?"**
1. [`docs/GUIDE.md`](docs/GUIDE.md) — install, weight placement, end-to-end commands
2. `voxprep --help` (and `voxprep <cmd> --help`) — every flag documented in-CLI
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §7 — directory map with per-file role

**"How was this built?"**
1. [`CLAUDE.md`](CLAUDE.md) — tutor-mode contract, Tidy First rules, ported-code boundary policy
2. [`docs/README.md`](docs/README.md) — phase index with links
3. [`docs/phases/phase01-bootstrap.md`](docs/phases/phase01-bootstrap.md) — what a phase guide looks like, including RED evolution
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — full object map (14 VOs, 1 Entity, 11 Services) with Mermaid diagrams per stage
5. [`docs/phases/phase19-odp-refinement.md`](docs/phases/phase19-odp-refinement.md) — honest self-review against Noback's 46 rules + fix plan
6. [`learnings/`](learnings/) — real questions from hands-on phases

The git log is deliberately readable: every commit is a Tidy First step (`feat:` / `refactor:` / `test:` / `docs:` / `chore:`), no mixed commits.

---

## Credits

voxprep stands on top of **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** by [RVC-Boss](https://github.com/RVC-Boss) and contributors, MIT (Copyright © 2024 RVC-Boss).

- The preprocessing file formats, slicer heuristics, `.list` contract, and ASR defaults come from upstream's `tools/slicer2.py`, `tools/asr/fasterwhisper_asr.py`, and `GPT_SoVITS/prepare_datasets/1-get-text.py`
- The extract / training / inference stages in `src/voxprep/{extract,training,inference}/` are direct ports of upstream's `AR/`, `module/`, `text/`, `TTS_infer_pack/`, `eres2net/`, `s1_train.py`, `s2_train.py` — adapted only for import paths, Typer adapters, and voxprep's directory conventions. File-level attribution is kept via `# ported from …` comments where meaningful

If voxprep is useful to you, please star upstream too. The training and inference — the hard part — live there. voxprep cleans up the preprocessing loop around it and gives the whole lifecycle a single CLI home.

---

## References

- **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** — the upstream project
- **Object Design Style Guide** — Matthias Noback. 46 rules for services, entities, value objects, methods, architecture, testing. Reviewed against voxprep in [`docs/phases/phase19-odp-refinement.md`](docs/phases/phase19-odp-refinement.md)
- **Test Driven Development: By Example** — Kent Beck. Red-Green-Refactor, test-as-spec
- **Tidy First?** — Kent Beck. Structural vs behavioral change separation
- **[Typer](https://typer.tiangolo.com/)**, **[Rich](https://rich.readthedocs.io/)**, **[prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)** — the CLI craft trinity
- **[uv](https://docs.astral.sh/uv/)** — the fast package/project manager

---
