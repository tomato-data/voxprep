# voxprep 사용 가이드

voxprep은 GPT-SoVITS 기반 음성 합성 모델 제작 파이프라인을 하나의 CLI로 묶은 도구입니다. 원본 오디오를 넣으면 분할 → ASR → 검수 → 특징 추출 → 학습 → 추론까지 전 과정을 voxprep 하나로 돌릴 수 있습니다.

```
[영상/원본 오디오]
       │  (ffmpeg 으로 WAV 추출 — utils/extract_wav.py)
       ▼
[raw WAV]  ──slice──▶  chunks/*.wav
                              │
                        ──asr──▶  draft.list
                                      │
                                ──review──▶  final.list  (사람 검수)
                                                  │
                                            ──extract──▶  logs/{exp}/2..7-*.*  (BERT/HuBERT/SV/semantic)
                                                              │
                                                        ──train──▶  SoVITS .pth  +  GPT .ckpt
                                                                         │
                                                                   ──infer──▶  TTS wav
```

---

## 1. 설치

### 요구사항
- macOS (Apple Silicon 검증) 또는 Linux. Windows 미검증
- Python 3.12
- [uv](https://github.com/astral-sh/uv) — Python/패키지 매니저
- `ffmpeg` (시스템 PATH 에 있어야 함)

### 저장소 받기
```bash
git clone <repo> voxprep
cd voxprep
```

### 가상환경 + 의존성
`pyproject.toml`에 이미 필요한 의존성이 전부 등록되어 있습니다 (torch, transformers, pytorch-lightning 등 약 40개).

```bash
uv sync
```

한국어/일본어/중국어/영어/광둥어 텍스트 파이프라인 의존성이 전부 포함되어 있어 첫 sync 는 시간이 다소 걸립니다 (~2분, 디스크 ~3GB).

### ffmpeg
```bash
brew install ffmpeg        # macOS
sudo apt install ffmpeg    # Linux
```

### 전역 설치 (선택)
프로젝트 루트 밖에서도 `voxprep` 을 쓰고 싶다면:
```bash
uv tool install -e .
# 이후 어디서든:
voxprep --help
```

---

## 2. 사전훈련 모델 배치

voxprep 은 `models/pretrained/` 를 기본 모델 루트로 사용합니다. 필요한 파일 (총 ~2GB):

```
models/pretrained/
├── chinese-hubert-base/                          # 180M  — HuBERT (모든 언어 필수)
├── chinese-roberta-wwm-ext-large/                # 621M  — BERT  (중국어만 사용)
├── sv/pretrained_eres2netv2w24s4ep4.ckpt         # 103M  — 화자 벡터 (v2Pro)
├── v2Pro/
│   ├── s2Gv2Pro.pth                              # 150M  — SoVITS Generator (학습 시작점)
│   ├── s2Dv2Pro.pth                              # 450M  — Discriminator
│   ├── s2Gv2ProPlus.pth                          #       — v2ProPlus 변형
│   └── s2Dv2ProPlus.pth
├── s1v3.ckpt                                     # 148M  — GPT 사전훈련 (학습 시작점 + 폴백 추론)
└── fast_langdetect/lid.176.bin                   # 125M  — 언어 감지 (추론 시)
```

G2PW (중국어 G2P) ONNX 모델:
```
models/g2pw/G2PWModel/                            # 608M  — 중국어 처리 시에만 사용
```

### 다운로드 소스
GPT-SoVITS 공식 릴리스에 전부 포함되어 있습니다. 자세한 다운로드 URL은 https://github.com/RVC-Boss/GPT-SoVITS 참고. 이미 별도 디렉토리에 받아두었다면 심볼릭 링크 없이 **복사**해서 `models/pretrained/` 로 가져오세요 (voxprep이 단독으로 돌아야 함).

### 경로 오버라이드
기본 위치 대신 다른 경로를 쓰려면:
```bash
export VOXPREP_MODELS_ROOT=/path/to/models
# 또는 커맨드별로:
voxprep extract --models-root /path/to/models ...
```

---

## 3. 워크플로우 — 끝에서 끝까지

아래는 Korean voice 샘플을 `demo_v1` 이라는 실험 이름으로 학습·추론하는 시나리오입니다.

### 0. 원본 준비 — 영상 → WAV

```bash
python3 utils/extract_wav.py /path/to/source.mp4
# → /path/to/source.wav  (44100Hz, mono, PCM s16le)
```

이후 단일 파일 또는 디렉토리를 voxprep 에 넘깁니다. voxprep은 **디렉토리** 단위로 받으므로 wav 파일들을 한 폴더에 모아둡니다:

```bash
mkdir -p ~/Desktop/raw_audio
mv /path/to/source.wav ~/Desktop/raw_audio/
```

### 1~3. prep — slice + asr + review 한 번에

```bash
uv run voxprep prep ~/Desktop/raw_audio/ \
  --workspace ~/Desktop/datasets/test \
  --speaker demo \
  --sample-rate 44100 \
  --skip-review       # 검수는 별도 단계에서
```

산출물 구조 (`~/Desktop/datasets/test/`):
```
chunks/                # slice 결과 wav
draft.list             # asr 직후
final.list             # review 후 (--skip-review 시 draft 복사본)
```

`.list` 포맷: `audio_path|speaker|language|text`.

### 3.5. review — 사람 검수

자동 생성된 `final.list`는 ASR 오류·잘못 잘린 청크가 섞여 있습니다. 검수를 돌려야 학습 품질이 올라갑니다.

```bash
uv run voxprep review ~/Desktop/datasets/test/final.list
```

**키 조작**:
- `n` / `b` — 다음 / 이전 항목
- `Enter` — 오디오 재생
- `e` — 텍스트 인라인 편집 (prompt_toolkit, 현재 텍스트가 기본값)
- `d` — 항목 삭제 (확인 필요)
- `u` — 마지막 삭제/편집 undo
- `q` — 종료 (저장은 즉시 flush 되므로 그냥 종료)

**자동 플래그**: 빈 텍스트, 3글자 이하, 감탄사만(아/어/오/음/응/에이), 한국어 데이터에 비한글, 60자 이상, 구두점만 — 이런 항목에는 `⚠ code: message` 가 렌더에 표시됩니다.

**플래그 항목만 빠르게**:
```bash
uv run voxprep review ~/Desktop/datasets/test/final.list --auto-prune
```
플래그된 항목으로만 점프하며 `Delete 'text'? (y/N)` 만 물어봅니다. (Phase 18 예정: 풀 review UI 로 통합)

### 4. extract — 특징 추출

```bash
uv run voxprep extract \
  --list-file ~/Desktop/datasets/test/final.list \
  --wav-dir ~/Desktop/datasets/test/chunks \
  --exp-name demo_v1 \
  --version v2Pro
```

4단계가 자동 실행됩니다:
1. Text + BERT features (중국어 아니면 BERT 스킵)
2. HuBERT + 32kHz 리샘플
3. 화자 벡터 (v2Pro/v2ProPlus 만)
4. 시맨틱 토큰 (VQ 양자화)

산출물 (`logs/demo_v1/`):
```
2-name2text.txt        # 음소 + word2ph + 정규화 텍스트
3-bert/*.pt            # BERT 임베딩 (중국어만)
4-cnhubert/*.pt        # HuBERT SSL 특징
5-wav32k/*.wav         # 32kHz 리샘플
6-name2semantic.tsv    # 시맨틱 토큰
7-sv_cn/*.pt           # 화자 벡터 (v2Pro)
```

### 5. train — SoVITS (s2) 학습

```bash
uv run voxprep train sovits \
  --exp-name demo_v1 \
  --epochs 12 --save-every 4
```

> **epochs 는 save-every 의 배수로**. 마지막 epoch 가 저장 주기에 맞지 않으면 그 epoch 가 버려집니다. 예: `--epochs 10 --save-every 4` 면 epoch 10 은 저장 안 됨.

산출물: `models/trained/SoVITS_weights_v2Pro/demo_v1_eN_sM.pth`.

macOS CPU 기준 epoch 당 약 4~5 분.

### 6. train — GPT (s1) 학습

```bash
uv run voxprep train gpt \
  --exp-name demo_v1 \
  --epochs 20 --save-every 4
```

SoVITS 와 달리 PyTorch Lightning 기반. 산출물: `models/trained/GPT_weights_v2Pro/demo_v1-eN.ckpt`.

### 5+6 한 번에
```bash
uv run voxprep train all \
  --exp-name demo_v1 \
  --sovits-epochs 12 --gpt-epochs 20 --save-every 4
```

### 7. infer — 대화형 추론

가장 편한 방법 — `.list` 파일에서 참조 오디오 자동 선택:

```bash
uv run voxprep infer \
  --ref-list ~/Desktop/datasets/test/final.list \
  --autoselect
```

- `--autoselect`: 4~8초 duration, 15~50자 텍스트, 가급적 완결 문장 기준으로 최상 후보 자동 선택
- `--autoselect` 생략: 상위 8개 후보를 보여주고 번호로 선택
- `--ref-audio X.wav --ref-text "..."` 형태로 명시적 지정도 가능

참조 오디오 언어는 `.list` 엔트리에서 자동 추출, `--text-lang` 생략 시 참조 언어와 동일.

세션 흐름 (현재):
```
Loading models...
Ready. Type text (Ctrl+C to exit).

[1] 안녕하세요
Synthesizing...
Saved: ./infer_out/infer_001.wav
[자동 재생]
[2] 오늘 날씨가 좋네요
...
```

> 현재는 입력 즉시 저장 + 재생하는 단순 루프입니다. 같은 텍스트로 re-roll, 저장 여부 선택 등은 다음 UX 업데이트에서 추가 예정.

---

## 4. 명령어 레퍼런스

### `voxprep slice`
```
voxprep slice <input_dir> <output_dir>
  --sample-rate 32000 --threshold -34
  --min-length 4000 --min-interval 300 --hop-size 10
  --max-sil-kept 500 --max-amp 0.9 --alpha 0.25
```
무음 경계로 wav 를 분할하고 정규화. 기본값은 SETUP_GUIDE 검증값.

### `voxprep asr`
```
voxprep asr <input_dir> <output_list>
  --model-size large-v3-turbo --language ko
  --device auto --compute-type auto
  --beam-size 5 --vad --vad-min-silence-ms 700
  --speaker narrator
```
faster-whisper 기반. 언어 코드 목록: `--list-languages`.

### `voxprep review`
```
voxprep review <list_file>
  --auto-prune       # 플래그된 항목만 순회
```

### `voxprep prep`
```
voxprep prep <raw_dir>
  --workspace <dir> --speaker <name>
  --skip-review      # 검수는 건너뛰기
  [slice 옵션 전부 forward]
  [asr 옵션 전부 forward]
```

### `voxprep extract`
```
voxprep extract
  --list-file <final.list>
  --wav-dir <chunks dir>
  --exp-name <name>
  --version v2Pro
  [--models-root <path>] [--half/--no-half]
  [--skip-sv]          # v2Pro 에서 화자 벡터 건너뛰기
  [--exp-root <path>]  # logs/{exp_name} 루트 지정
```

### `voxprep train sovits|gpt|all`
```
voxprep train all --exp-name demo_v1
  --version v2Pro
  --sovits-epochs 12 --gpt-epochs 20
  --batch-size 1 --save-every 4
  --half/--no-half --gpus 0
  --dpo/--no-dpo          # GPT 에만 적용
```
subcommand `sovits`/`gpt` 는 각각 단독 실행.

### `voxprep infer`
```
voxprep infer
  [--sovits <pth> --gpt <ckpt>]   # 명시
  [--ref-audio <wav> --ref-text "..."]
  [--ref-list <list> [--autoselect]]
  --version v2Pro
  [--output-dir <dir>] [--no-play]
```
weight 미지정 시 `models/trained/<SoVITS|GPT>_weights_v2Pro/` 에서 번호로 선택.

---

## 5. 디렉토리 구조 요약

```
voxprep/                              # 프로젝트 루트
├── src/voxprep/                      # 패키지
│   ├── cli.py                        # Typer app
│   ├── commands/                     # 얇은 CLI 어댑터
│   ├── parsing/                      # .list 포맷 (VO)
│   ├── slicing/                      # slice 로직 + Slicer Service
│   ├── transcription/                # faster-whisper 래퍼
│   ├── review/                       # 검수 TUI
│   ├── pipeline/                     # prep 파이프라인
│   ├── extract/                      # 특징 추출 (이식)
│   │   ├── text_features.py, hubert_features.py, speaker_vectors.py, semantic_tokens.py
│   │   ├── text/                     # 언어별 음소 변환 (이식)
│   │   ├── module/                   # SoVITS VQ 모델 (이식)
│   │   ├── eres2net/                 # 화자 벡터 모델 (이식)
│   │   └── configs/                  # s2/s1 템플릿
│   ├── training/                     # SoVITS + GPT 학습 (이식)
│   │   ├── s2_train.py, s1_train.py
│   │   ├── AR/                       # GPT 모델
│   │   └── config_builder.py
│   └── inference/                    # 추론 (이식)
│       ├── tts_pack/                 # TTS 클래스 (이식)
│       ├── ref_picker.py             # 참조 오디오 랭킹
│       └── session.py                # InferenceSession 래퍼
├── tests/                            # 단위 + 통합 테스트 (73개)
├── docs/                             # phase 문서 + 이 가이드
├── models/                           # 사전훈련 모델 (.gitignore)
├── logs/                             # 실험 산출물 (.gitignore)
├── infer_out/                        # 추론 wav (.gitignore)
└── GPT-SoVITS/                       # 참조용 원본 (.gitignore, 이식 끝나면 삭제)
```

---

## 6. 팁 & 트러블슈팅

### sample rate 불일치
`ValueError: expected sample rate 32000, got 44100` — `voxprep prep`/`slice` 의 `--sample-rate` 값을 입력 wav 에 맞춰 주세요.

### `torchcodec` 누락 에러
torchaudio 2.11 이 torchcodec 백엔드를 기본으로 요구합니다. voxprep 은 scipy/librosa 기반 로드로 우회했으므로 torchcodec 설치는 불필요합니다. 그래도 에러가 나면 해당 코드가 torchaudio.load 를 직접 부르는지 확인하세요.

### macOS MPS
MPS 는 현재 CTranslate2 / 일부 HuBERT 경로에서 불안정합니다. voxprep 은 CUDA 부재 시 CPU 로 폴백. 학습은 CPU 기준 overnight. 본격 학습은 CUDA 머신 권장.

### 학습 epoch 수
`save-every` 의 배수로 맞춥니다. 안 맞추면 마지막 epoch 가 저장되지 않습니다.

### 참조 오디오 고르기
- 4~8초 완결 문장
- 감정 극단 회피 (크게 웃음, 비명 등)
- 깨끗한 녹음 (리버브/노이즈 없음)
- `--ref-list ... --autoselect` 면 자동으로 적절한 후보 선택됨

### 학습한 GPT 없이 추론
`models/trained/GPT_weights_v2Pro/` 가 비어 있으면 `s1v3.ckpt`(사전훈련) 로 폴백. 음색은 학습된 SoVITS 를 따라가지만 억양·문장 구조는 원 화자 특성이 덜 반영됨. GPT 학습 완료 후 재시도 권장.

---

## 7. 현재 구현 상태

✅ **완료된 Phase**:
- 01~10: 전처리 파이프라인 (slice → asr → review → prep)
- 13: 특징 추출 (text/HuBERT/SV/semantic 이식 + Typer 통합)
- 14: 학습 파이프라인 (s2_train + s1_train + AR/ 이식)
- 15: 추론 (TTS_infer_pack 이식 + 대화형 CLI 세션)

⏳ **진행/예정**:
- 11: 진행률 표시 개선 (긴 작업에 Rich Live)
- 12: `voxprep to-wav` (현재는 utils/extract_wav.py 직접 호출)
- 16: tkinter GUI 추론 (파형 뷰, 파라미터 슬라이더, 결과 비교)
- 17: REST/MCP 서버 (LLM tool use 연계)
- 18: `review` 루프 통합 (auto-prune 에 풀 UI)

자세한 phase 내역은 [`docs/README.md`](README.md) 참조.

---

## 8. 추가 학습 자원

- TDD 원칙: `~/.claude/skills/tdd/`
- ODP 46 규칙: `~/.claude/skills/object-design-practices/`
- GPT-SoVITS 원본: https://github.com/RVC-Boss/GPT-SoVITS
- Typer: https://typer.tiangolo.com/
- Rich: https://rich.readthedocs.io/
