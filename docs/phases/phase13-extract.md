# Phase 13 — `extract` 특징 추출 파이프라인

## 사용자 시점

```bash
voxprep extract --workspace ./datasets/myvoice --exp-name myvoice_v1
```

## 배경

GPT-SoVITS 학습 전 3단계 특징 추출이 필요. **전부 자동** — 사용자 개입 없음.

### 3단계 파이프라인

| 단계 | 원본 스크립트 | 입력 | 출력 | 설명 |
|------|-------------|------|------|------|
| 1 | `1-get-text.py` | final.list + 오디오 | `2-name2text.txt`, `3-bert/*.pt` | 텍스트→음소 변환 + BERT 임베딩 추출 |
| 2 | `2-get-hubert-wav32k.py` | final.list + 오디오 | `4-cnhubert/*.pt`, `5-wav32k/*.wav` | HuBERT SSL 특징 + 32kHz 리샘플링 |
| 3 | `3-get-semantic.py` | HuBERT 출력 | `6-name2semantic.tsv` | VQ-VAE로 시맨틱 토큰 양자화 |

### 출력 구조

```
logs/{exp_name}/
├── 2-name2text.txt
├── 3-bert/*.pt
├── 4-cnhubert/*.pt
├── 5-wav32k/*.wav
└── 6-name2semantic.tsv
```

## 구현 전략

- 원본 스크립트를 **subprocess로 호출** (in-process 이식은 의존성이 너무 무거움)
- 환경변수로 파라미터 전달 (원본 스크립트가 이 방식을 기대)
- 단계별 Rich Progress 표시
- 각 단계 완료 여부를 출력 파일 존재로 판단 → skip 가능

## 의존성

- 사전훈련 모델: BERT, CNHuBERT, SoVITS VQ (GPT-SoVITS에 포함)
- GPU 권장이지만 CPU에서도 동작 (느림)
- macOS: MPS 미지원 → CPU 폴백
