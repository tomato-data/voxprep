# voxprep

[![English](https://img.shields.io/badge/lang-English-blue)](README.md)

> GPT-SoVITS의 전 라이프사이클(**전처리 → 특징 추출 → 학습 → 추론**)을 하나의 CLI로. 업스트림에는 없는 **대화형 `review` 단계**와 함께.

> [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) (MIT) 위에 빌드한 프로젝트입니다. 전처리 루프는 TDD + ODP로 처음부터 다시 짓고, 특징 추출·학습·추론은 업스트림 모듈을 패키지 안으로 이식해 한 CLI 안에 묶었습니다.

## Highlights

- **GPT-SoVITS에 없는 `review` 단계** — ASR 결과를 사람이 검수하는 키보드 중심 TUI. 인라인 오디오 재생(Enter), 인라인 편집(`e`), 삭제/undo(`d`/`u`), 그리고 자동 플래그(빈 텍스트·감탄사·비한글 잡음·3글자 이하 등)
- **GPT-SoVITS에 없는 참조 오디오 자동 선택** — `voxprep infer` 가 `.list` 파일을 읽어 후보를 점수화합니다. 지속 시간(4~8초), 텍스트 길이(15~50자), 문장 완결성 기준. `--autoselect` 로 최상 1개 바로 지정, 생략 시 상위 8개를 대화형으로 선택. 언어 코드도 `.list` 엔트리에서 자동 추출
- **전 라이프사이클이 하나의 CLI 안에** — `slice → asr → review → prep → extract → train → infer` 전부 터미널에서 조합 가능. 브라우저 불필요. 업스트림이 노출하는 모든 노브는 `--flag` 로 그대로 접근 가능하며, 프로젝트 단위 기본값을 한 번에 지정하는 설정 파일도 계획됩니다 ([Phase 20](docs/phases/phase20-config-file.md))
- **검증된 기본값** — macOS Apple Silicon + 한국어 음성을 일차 환경으로 가정한 기본값(`--language ko`, `--model-size large-v3-turbo`, CTranslate2용 CPU 폴백). WebUI 기본값이 아니라 엔드 투 엔드로 실제 검증된 값을 그대로 반영
- **자체 완결** — 특징 추출·학습·추론이 GPT-SoVITS 레포를 subprocess 로 호출하지 않습니다. 필요한 모듈(`AR/`, `module/`, `TTS_infer_pack/`, `text/`, `eres2net/`)을 `src/voxprep/{extract,training,inference}/` 로 이식해서, 외부 의존성은 사전훈련 가중치 파일뿐
- **전처리는 손으로 구축, ML 코어는 이식** — Phase 01~10(전처리)은 튜터 모드에서 실패 테스트 한 번에 하나씩 손으로 타이핑. VITS + GPT 디코더를 처음부터 다시 쓰는 건 이 프로젝트의 목표가 아니었으므로 Phase 13~15(ML 파이프라인)는 업스트림에서 바로 이식해서 최소 수정만 적용.

> **현재 진행 상황**: Phase 01~15 완료. macOS에서 전 파이프라인이 엔드 투 엔드로 돌아갑니다. 남은 로드맵: 진행률 표시(11), `to-wav` 유틸(12), tkinter GUI(16), MCP/REST 서버(17), review 루프 통합(18), ODP 정제(19), 설정 파일 지원(20).

엔드 투 엔드 사용법은 [**`docs/GUIDE.md`**](docs/GUIDE.md), 객체 디자인 전체 지도는 [**`docs/ARCHITECTURE.md`**](docs/ARCHITECTURE.md).

---

## 왜 만들었나

GPT-SoVITS는 훌륭히 음성 합성 모델을 학습시키는 데 필요한 모든 것을 제공하지만, 실제로 쓰려고 해보면 WebUI와 반(半)독립적인 스크립트들(`slicer2.py`, `fasterwhisper_asr.py`, `1-get-text.py`)로 조각나 있어 각자의 버튼·드롭다운·가정을 따로 알아야 했습니다.

반복적으로 부딪힌 마찰 두 가지:

1. **CLI 루프가 깨져 있다.** 한 배치에 대해 `slice → asr → review → prep` 을 돌리려고 브라우저를 열 이유가 없습니다. 기존 도구는 탭 전환을 계속 요구하고, 조합이 매끄럽지 않고, 기본값이 참조 구성에 맞춰져 있어 매번 같은 플래그를 다시 설정해야 합니다.
2. **`review` 단계가 아예 없다.** Whisper 의 ASR 결과는 `.list` 파일(`audio_path|speaker|language|text`)로 떨어지는데 이를 편집할 환경이 제공되지 않습니다. `vim` 이나 여타 에디터로 수백 줄을 스크롤하면서 실제 음성을 듣고 텍스트를 고치는 환경이 있었으면 좋겠다고 생각했습니다.

그래서 전처리 파이프라인을 제대로 된 CLI 로 다시 짓고, **`review` 단계를 직접 추가**합니다 — 키보드 중심, 인라인 오디오 재생, 인라인 편집, 삭제/undo, 문제 줄 자동 플래그까지. 또한 라이프사이클 전체가 한 CLI 안에 들어온 뒤로는 추론 시 참조 오디오를 매번 손으로 고르는 일도 마찰이 되어, **참조 오디오 자동 선택**도 함께 붙였습니다 — `.list` 엔트리의 지속 시간·텍스트 길이·문장 완결성을 점수화해 최상 후보 1개를 바로 지정(`--autoselect`)하거나 상위 8개를 대화형으로 보여주는 모드까지.

이 프로젝트는 실용 목적과 함께 **TDD Red-Green-Refactor**(Kent Beck), **Tidy First** 커밋 분리, **Object Design Practices**(Matthias Noback 46규칙)를 체화하는 연습이기도 합니다. 전처리 Phase 는 실패 테스트부터 시작해 손으로 한 줄씩 구현했고, 모든 구조적 결정은 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) 에, ODP 재검토와 개선 계획은 [`docs/phases/phase19-odp-refinement.md`](docs/phases/phase19-odp-refinement.md) 에 기록해두었습니다.

---

## 파이프라인 한눈에

```
[영상 / 원본 오디오]
       │  (utils/extract_wav.py — ffmpeg)
       ▼
[원본 WAV]
       │
  voxprep prep ──▶  slice → asr → review
       │                            │
       │                            ▼
       ▼                    logs/{exp}/final.list
  chunks/*.wav                      │
                                    ▼
                           voxprep extract ──▶ BERT + HuBERT + 화자 벡터 + 시맨틱 토큰
                                    │
                                    ▼
                           voxprep train {sovits, gpt, all}
                                    │
                                    ▼
                           models/trained/{SoVITS,GPT}_weights_v2Pro/*.{pth,ckpt}
                                    │
                                    ▼
                           voxprep infer ──▶  대화형 TTS 세션
```

각 화살표는 `uv run voxprep …` 한 커맨드. 각 디렉토리마다 계약이 문서화되어 있고, 필요시 skip/rerun 자동 판단.

---

## 어떻게 만들어졌나

프로젝트는 두 저작 모드가 섞여 있습니다:

**튜터 모드 (Phase 01~10)** — 전처리 + review. `src/voxprep/parsing/`, `slicing/`, `transcription/`, `review/`, `pipeline/` 의 모든 줄은 Claude 를 RED 사이클 튜터로 두고 제가 직접 타이핑했습니다. Claude 가 실패하는 테스트를 써주면 제가 타이핑해서 `ModuleNotFoundError → ImportError → AttributeError → AssertionError` 진화를 보고, 그 시점에서 GREEN 에 도달하는 최소 프로덕션 코드를 작성. REFACTOR 는 별도 커밋, ODP 로 분류, 섣부른 추상화 금지. Q&A 는 [`learnings/phaseNN-qa.md`](learnings/) 에 그때그때 기록.

**이식 모드 (Phase 13~15)** — 특징 추출, 학습, 추론. 업스트림의 이 영역은 규모가 크고 이미 검증된 코드라, 처음부터 다시 쓰는 건 이 프로젝트의 목표가 아니었습니다. Claude 가 기계적 이식을 담당: 파일을 `src/voxprep/{extract,training,inference}/` 로 복사, `from text.X` → `from voxprep.extract.text.X` 로 import 재작성, 기존 엔트리 함수를 Typer 어댑터로 감싸기, 의존성 조정. 이식 경계는 명확히 유지해서 나중에 업스트림에서 다시 당겨오거나 격리하기 쉽게.

---

## 로드맵

| Part | Phase | 산출물 | 상태 |
|------|-------|--------|------|
| A: 전처리 (TDD 재구성) | 01 부트스트랩 — Typer + pytest | `voxprep version` | ✅ |
|  | 02 `.list` 파서 (Value Object) | `ListEntry` | ✅ |
|  | 03 `slice` 커맨드 | `voxprep slice` | ✅ |
|  | 04 `asr` 커맨드 | `voxprep asr` | ✅ |
|  | 05~09 `review` (이동/재생/편집/삭제+undo/자동 플래그) | `voxprep review [--auto-prune]` | ✅ |
|  | 10 `prep` 파이프라인 | `voxprep prep` | ✅ |
| B: UX + 유틸 | 11 진행률 표시 (Rich Live) | — | ⏳ |
|  | 12 `to-wav` (영상 → WAV) | `voxprep to-wav` | ⏳ |
|  | 18 review 루프 통합 (auto-prune 에 풀 UI) | — | ⏳ |
| C: 특징 추출 + 학습 (이식) | 13 `extract` | `voxprep extract` | ✅ |
|  | 14 `train {sovits,gpt,all}` | `voxprep train …` | ✅ |
| D: 추론 (이식) | 15 `infer` CLI 세션 + 참조 오디오 자동 선택 | `voxprep infer [--autoselect]` | ✅ |
|  | 16 tkinter GUI | 독립 앱 | ⏳ |
|  | 17 MCP / REST (LLM tool-use) | 서비스 | ⏳ |
| E: 정제 | 19 ODP 46규칙 기반 리팩터 | 구조 개선 | ⏳ |
|  | 20 설정 파일 + CLI 오버라이드 체계 | `voxprep config {show,init,edit,path}` | ⏳ |

범례: ✅ 완료 · 🔄 진행 중 · ⏳ 예정

각 Phase 가이드는 [`docs/phases/`](docs/phases/), 핸즈온 사용 매뉴얼은 [`docs/GUIDE.md`](docs/GUIDE.md), 디자인 맵은 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## `.list` 포맷

모든 단계를 연결하는 데이터 계약:

```
audio_path|speaker_name|language|text
```

- `|` 로 구분된 4 필드 (`text` 안에 파이프 포함 시 양방향 모두 파싱 에러)
- UTF-8, 줄바꿈 구분, **파일 끝 개행 없음** (원본의 `"\n".join(...)` 과 일치)
- 언어 코드는 **파서 경계에서 소문자로 정규화** — [경계에서 정규화 원칙](learnings/DISCOVERIES.md) 참고

이 파서가 voxprep 의 첫 Value Object 이자 "데이터는 경계에서 검증한다" 원칙이 처음 강제되는 자리입니다.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| **언어** | Python 3.12 (`.python-version` 으로 고정) |
| **CLI** | Typer 0.24 — 서브커맨드 그룹, 자동 `--help` |
| **터미널** | Rich — 컬러, 테이블, 진행률 |
| **대화형 입력** | prompt_toolkit — 인라인 편집, raw-mode 키 읽기 |
| **ASR** | faster-whisper + CTranslate2 (macOS CPU, 그 외 CUDA) |
| **ML 스택** | torch 2.11, torchaudio, transformers ≤ 4.50, pytorch-lightning, peft |
| **오디오** | librosa 0.10, scipy, soundfile, numpy < 2.0, ffmpeg-python |
| **텍스트 처리** | pypinyin, jieba, pyopenjtalk, g2p_en, jamo, ko_pron, g2pk2, python-mecab-ko, ToJyutping |
| **테스트** | pytest 9 + Typer `CliRunner` — 73 테스트, 단위 + 통합 (`tmp_path` e2e) |
| **패키지 관리** | [uv](https://github.com/astral-sh/uv) (`uv sync`, 커밋된 `uv.lock`) |

직접 의존성이 Phase 15 시점 약 40개. 사전훈련 가중치까지 포함하면 venv + models 합쳐 ~5GB 규모.

---

## 프로젝트 구조

```
voxprep/
├── src/voxprep/
│   ├── cli.py                      # Typer 앱 — 모든 서브커맨드 등록
│   ├── commands/                   # 얇은 CLI 어댑터 (서브커맨드 1:1)
│   │   ├── slice.py, asr.py, review.py, prep.py
│   │   ├── extract.py, train.py, infer.py
│   ├── parsing/                    # .list 파서 (ListEntry VO + errors)
│   ├── slicing/                    # Slicer Service + Chunk VO + SliceOptions VO
│   ├── transcription/              # WhisperTranscriber + WhisperLike Protocol + AsrOptions
│   ├── review/                     # ReviewSession Entity + Dispatcher + issues + players
│   ├── pipeline/                   # Workspace VO + slice_step/asr_step/review_step
│   ├── extract/                    # ▼▼ 이식본 ▼▼  BERT/HuBERT/SV/semantic 추출
│   │   ├── text_features.py, hubert_features.py, speaker_vectors.py, semantic_tokens.py
│   │   ├── cnhubert.py, audio_utils.py, hparams.py, models_path.py
│   │   ├── text/                   # 업스트림 text/ — 음소 변환 (28 파일, 다국어)
│   │   ├── module/                 # 업스트림 module/ — SoVITS VQ + 지원 (16 파일)
│   │   ├── eres2net/               # 업스트림 화자 벡터 모델
│   │   └── configs/                # s1/s2 설정 템플릿
│   ├── training/                   # ▼▼ 이식본 ▼▼  SoVITS (s2) + GPT (s1) 학습
│   │   ├── s2_train.py, s1_train.py, process_ckpt.py, utils.py
│   │   ├── AR/                     # 업스트림 AR/ — GPT 모델
│   │   ├── config_builder.py       # SovitsTrainOptions / GptTrainOptions VO
│   │   └── i18n/                   # 업스트림 locale 파일
│   └── inference/                  # ▼▼ 이식본 ▼▼  TTS 추론
│       ├── session.py              # InferenceSession + InferenceInputs VO
│       ├── ref_picker.py           # RefCandidate VO + rank_candidates
│       ├── sv.py, tts_pack/        # 업스트림 TTS_infer_pack
│
├── tests/                          # 73 테스트 (단위 + 통합)
│   ├── fixtures/                   # 공용 더블 (FakeWhisperModel, SpyPlayer, …)
│   ├── unit/                       # in-process
│   └── integration/                # CliRunner + tmp_path e2e
│
├── docs/
│   ├── README.md                   # Phase 인덱스 (로드맵 뷰)
│   ├── GUIDE.md                    # 엔드 투 엔드 사용 가이드 (설치 → 추론)
│   ├── ARCHITECTURE.md             # ODP 분류 맵 + Mermaid 다이어그램
│   └── phases/                     # 각 Phase 가이드 (phase01 … phase20)
│
├── learnings/                      # 사용자 저작 Q&A + 발견
│
├── models/                         # (.gitignore) 사전훈련 + 학습 가중치
│   ├── pretrained/                 # chinese-hubert-base, v2Pro, sv, s1v3.ckpt, …
│   └── trained/                    # SoVITS_weights_v2Pro, GPT_weights_v2Pro
│
├── logs/                           # (.gitignore) 실험별 특징 추출 산출물
├── infer_out/                      # (.gitignore) voxprep infer 로 생성된 WAV
│
├── CLAUDE.md                       # 튜터 모드 계약 + 프로젝트 전체 규칙
├── .python-version                 # 3.12
├── pyproject.toml
└── uv.lock                         # 재현성을 위해 추적
```

`models/`, `logs/`, `infer_out/`, `GPT-SoVITS/`(vendor 참조본)은 모두 gitignore. 가중치는 별도 다운로드([`docs/GUIDE.md`](docs/GUIDE.md) §2 참조).

---

## 실행

**요구 사항:** [uv](https://docs.astral.sh/uv/) (필요하면 Python 3.12 자동 설치), 시스템 PATH 에 `ffmpeg`.

```bash
git clone https://github.com/tomato-data/voxprep.git
cd voxprep
uv sync                              # 첫 설치 ~2분, torch + transformers + 텍스트 deps 포함

uv run pytest tests/ -v              # 73개 통과
uv run voxprep --help                # 전체 커맨드 표면
```

이후 사전훈련 가중치를 [`docs/GUIDE.md`](docs/GUIDE.md) §2 에 따라 `models/pretrained/` 에 배치하면 전 파이프라인 실행 준비 완료.

최소 엔드 투 엔드 스모크 테스트 (한국어, v2Pro, MP3/MP4 시작):

```bash
python3 utils/extract_wav.py /path/to/source.mp4
mv /path/to/source.wav ~/Desktop/raw_audio/

uv run voxprep prep ~/Desktop/raw_audio \
  --workspace ~/Desktop/datasets/demo --speaker demo \
  --sample-rate 44100 --skip-review

uv run voxprep review ~/Desktop/datasets/demo/final.list          # 키보드 기반 검수
uv run voxprep extract --list-file ~/Desktop/datasets/demo/final.list \
                       --wav-dir ~/Desktop/datasets/demo/chunks \
                       --exp-name demo_v1

uv run voxprep train all --exp-name demo_v1 \
                         --sovits-epochs 12 --gpt-epochs 20 --save-every 4

uv run voxprep infer --ref-list ~/Desktop/datasets/demo/final.list --autoselect
```

각 커맨드에 `--help` 지원, 업스트림 노브는 전부 플래그로 접근 가능.

---

## 읽는 순서 (학습 목적으로 오셨다면)

목적에 따라 두 경로:

**"이거 어떻게 쓰나?"**
1. [`docs/GUIDE.md`](docs/GUIDE.md) — 설치, 가중치 배치, 엔드 투 엔드 커맨드
2. `voxprep --help` (와 `voxprep <cmd> --help`) — 모든 플래그가 CLI 안에 문서화
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §7 — 파일별 역할이 달린 디렉토리 맵

**"이거 어떻게 만들어졌나?"**
1. [`CLAUDE.md`](CLAUDE.md) — 튜터 모드 계약, Tidy First 규칙, 이식 코드 경계 정책
2. [`docs/README.md`](docs/README.md) — Phase 인덱스와 각 문서 링크
3. [`docs/phases/phase01-bootstrap.md`](docs/phases/phase01-bootstrap.md) — Phase 가이드 예시 (RED 진화 시나리오 포함)
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 전체 객체 맵 (14 VO, 1 Entity, 11 Service) + 각 단계 Mermaid 다이어그램
5. [`docs/phases/phase19-odp-refinement.md`](docs/phases/phase19-odp-refinement.md) — Noback 46규칙 기반 자체 평가 + 개선 계획
6. [`learnings/`](learnings/) — 각 Phase 실제 질의응답

git log 도 의도적으로 읽을 만하게 구성했습니다. 모든 커밋이 Tidy First 단위(`feat:` / `refactor:` / `test:` / `docs:` / `chore:`), 혼합 커밋 없음.

---

## 크레딧

voxprep 은 [RVC-Boss](https://github.com/RVC-Boss) 와 기여자들이 만든 **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** 위에서 동작합니다. GPT-SoVITS 는 MIT 라이선스(Copyright © 2024 RVC-Boss).

- 전처리 파일 포맷, 슬라이서 휴리스틱, `.list` 계약, ASR 기본값은 업스트림의 `tools/slicer2.py`, `tools/asr/fasterwhisper_asr.py`, `GPT_SoVITS/prepare_datasets/1-get-text.py` 에서 가져옴
- `src/voxprep/{extract,training,inference}/` 안의 특징 추출·학습·추론 단계는 업스트림의 `AR/`, `module/`, `text/`, `TTS_infer_pack/`, `eres2net/`, `s1_train.py`, `s2_train.py` 를 직접 이식한 것 — import 경로, Typer 어댑터, voxprep 디렉토리 컨벤션에 맞춰 최소 수정만. 의미 있는 위치에는 `# ported from …` 주석으로 파일 단위 출처 보존

voxprep 이 유용하셨다면 업스트림에도 스타 한 번 눌러주시면 좋겠습니다. 학습과 추론 — 진짜 무거운 부분 — 은 전부 업스트림이 하고, voxprep 은 그 앞뒤를 정리해 한 CLI 안에 묶은 것뿐입니다.

---

## 참고 자료

- **[GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)** — 업스트림 프로젝트
- **Object Design Style Guide** — Matthias Noback. 서비스·엔티티·Value Object·메서드·아키텍처·테스트에 대한 46규칙. voxprep 에 적용한 리뷰: [`docs/phases/phase19-odp-refinement.md`](docs/phases/phase19-odp-refinement.md)
- **Test Driven Development: By Example** — Kent Beck. Red-Green-Refactor, 테스트가 곧 명세
- **Tidy First?** — Kent Beck. 구조 변경과 행동 변경의 커밋 분리
- **[Typer](https://typer.tiangolo.com/)**, **[Rich](https://rich.readthedocs.io/)**, **[prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)** — CLI craft 3종 세트
- **[uv](https://docs.astral.sh/uv/)** — 빠른 패키지/프로젝트 매니저

---
