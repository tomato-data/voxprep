# Phase 13 — `extract` 특징 추출 파이프라인 (이식)

## 기본 방침

**`voxprep/GPT-SoVITS/`는 참고용(.gitignore됨)**. 이 단계부터는 필요한 파이썬 소스를 **voxprep 안으로 이식(copy + adapt)**해서 voxprep이 런타임에 외부 폴더를 참조하지 않는 자체 완결 구조로 만든다.

- "이식만 하는 느낌" — 알고리즘/모델 코드는 그대로 복사. 단 Typer 어댑터, voxprep 네이밍, import 경로만 조정
- 이식 끝난 파일은 `voxprep/GPT-SoVITS/` 에서 삭제
- 의존성(torch, transformers, librosa, pytorch-lightning 등)은 **voxprep venv에 직접 설치**

## 사용자 시점

```bash
voxprep extract \
  --list-file ./datasets/myvoice/final.list \
  --wav-dir ./datasets/myvoice/chunks \
  --exp-name myvoice_v1
```

- `exp_name`은 **extract → train → infer**의 전 단계를 잇는 식별자. `logs/{exp_name}/` 아래에 모든 중간 산출물, 최종 weights 파일명도 `{exp_name}-e{epoch}.*`

## 이식 대상

| 이식 원본 (GPT-SoVITS) | voxprep 경로 | 설명 |
|----------------------|-------------|------|
| `GPT_SoVITS/prepare_datasets/1-get-text.py` | `src/voxprep/extract/text_features.py` | 텍스트→음소, BERT 임베딩 |
| `GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py` | `src/voxprep/extract/hubert_features.py` | HuBERT + 32kHz 리샘플 |
| `GPT_SoVITS/prepare_datasets/2-get-sv.py` | `src/voxprep/extract/speaker_vectors.py` | Speaker vector (v2Pro) |
| `GPT_SoVITS/prepare_datasets/3-get-semantic.py` | `src/voxprep/extract/semantic_tokens.py` | VQ 양자화 |
| `GPT_SoVITS/text/` (언어별 클리너) | `src/voxprep/extract/text/` | 음소 변환, 언어별 규칙 |
| `GPT_SoVITS/feature_extractor/cnhubert.py` | `src/voxprep/extract/cnhubert.py` | HuBERT 래퍼 |
| `GPT_SoVITS/module/models.py`의 VQ 부분 | `src/voxprep/extract/vq.py` | `extract_latent` |

## 사전훈련 모델

런타임에 필요한 weights (사용자가 직접 다운로드):
- BERT (chinese-roberta-wwm-ext-large)
- CNHuBERT (chinese-hubert-base)
- SoVITS VQ (s2Gv2Pro.pth 등, 버전별)
- (v2Pro만) Speaker vector ckpt

`src/voxprep/models/` 디렉토리(.gitignore)에 배치하고, `--models-root`로 오버라이드 가능.

SETUP_GUIDE 2절 참조.

## 의존성 추가

Phase 13 시작 전에 `uv add`:

```bash
uv add torch torchaudio transformers librosa numpy<2.0 pyyaml
# + 특징 추출 단계 한정 추가 의존성 (pyopenjtalk, jieba, g2p_en 등) — 이식할 코드가 쓰는 것만 점진 추가
```

## 단계별 이식 순서 (sub-phases)

### 13a — 인프라 & 경로
- `src/voxprep/models/` 경로 해석 (환경변수/CLI 오버라이드)
- weights 파일 존재 검증 (없으면 다운로드 안내)

### 13b — text_features (1-get-text)
- 언어별 클리너 의존성 (`text/cleaner.py`, 각 언어 모듈)만 골라서 이식
- 한국어 전용 경로가 voxprep의 주 사용이므로 ko 우선
- 나머지 언어는 점진 추가

### 13c — hubert_features (2-get-hubert-wav32k)
- CNHuBERT 모델 로더 이식
- 오디오 정규화 로직 그대로

### 13d — speaker_vectors (2-get-sv, v2Pro만)

### 13e — semantic_tokens (3-get-semantic)
- VQ 모델 이식
- SoVITS `module/models.py`의 Generator 부분만 (전체 말고)

### 13f — Typer 커맨드 통합
- `voxprep extract`로 a~e를 순차 호출
- Rich Live로 단계 진행 표시 (Phase 11과 맞물림)

## ODP 관점

- 모델 로더(cnhubert, vq) — Service
- 특징 추출 함수 — 자유 함수 (입력 → 출력)
- FeatureExtractionResult — Value Object (파일 경로 묶음)
- ExtractOptions — Value Object

## 완료 기준

- [ ] `uv run voxprep extract` 한 번에 `logs/{exp_name}/` 아래 전체 파일 생성
- [ ] `voxprep/GPT-SoVITS/GPT_SoVITS/prepare_datasets/` 삭제 가능
- [ ] 이식된 코드가 voxprep venv 안에서 subprocess 없이 동작
- [ ] 사전훈련 모델 경로가 `src/voxprep/models/` 또는 `--models-root`로 해석

## 주의

- 용량: torch + transformers + 사전훈련 모델로 venv/모델이 수 GB가 됨 — 정상
- macOS: MPS 미지원 모듈 있음 → CPU 폴백
- 라이선스: GPT-SoVITS는 MIT. 이식 시 원본 출처 주석으로 명기 (`# ported from GPT_SoVITS/prepare_datasets/1-get-text.py`)
