# Phase 14 — `train` SoVITS + GPT 학습 (이식)

## 기본 방침

Phase 13과 동일. GPT-SoVITS 학습 코드를 voxprep 안으로 **이식**. subprocess 호출 금지. 이식 끝나면 `voxprep/GPT-SoVITS/` 에서 해당 파일 삭제.

## 사용자 시점

```bash
voxprep train all --exp-name myvoice_v1
voxprep train sovits --exp-name myvoice_v1
voxprep train gpt --exp-name myvoice_v1
```

## 이식 대상

| 원본 | voxprep 경로 | 설명 |
|------|-------------|------|
| `GPT_SoVITS/s2_train.py` | `src/voxprep/training/sovits_trainer.py` | SoVITS 학습 메인 |
| `GPT_SoVITS/s1_train.py` | `src/voxprep/training/gpt_trainer.py` | GPT 학습 메인 (PyTorch Lightning) |
| `GPT_SoVITS/module/models.py` | `src/voxprep/training/sovits/models.py` | Generator + Discriminator |
| `GPT_SoVITS/module/data_utils.py` | `src/voxprep/training/sovits/data.py` | Dataset, collate |
| `GPT_SoVITS/AR/` | `src/voxprep/training/gpt/` | Autoregressive GPT 모델 |
| `GPT_SoVITS/configs/s2v2Pro.json` | `src/voxprep/training/configs/s2v2Pro.json` | SoVITS 템플릿 |
| `GPT_SoVITS/configs/s1longer-v2.yaml` | `src/voxprep/training/configs/s1longer-v2.yaml` | GPT 템플릿 |
| `GPT_SoVITS/utils.py` | `src/voxprep/training/utils.py` | 공용 utils (이식 시 골라서) |

## 단계별 이식 순서 (sub-phases)

### 14a — 공용 인프라
- `src/voxprep/training/configs/` 에 JSON/YAML 템플릿 복사
- ConfigBuilder 이식 (`build_sovits_config`, `build_gpt_config`)
- WeightsPaths (버전별 weights 디렉토리 해석) — 이식, voxprep 관례에 맞게 수정

### 14b — SoVITS (s2_train)
- `module/models.py`의 Generator, Discriminator 이식
- `module/data_utils.py` Dataset 이식
- `s2_train.py`를 `sovits_trainer.py` 로 적응 — argparse → 함수 API
- DDP/distributed 로직: 단일 GPU(또는 CPU) 경로만 우선 유지, 분산은 이식 보류
- Typer: `voxprep train sovits`

### 14c — GPT (s1_train)
- `AR/` 전체 이식 (model, modules, utils)
- PyTorch Lightning trainer 이식
- `s1_train.py` → `gpt_trainer.py`
- Typer: `voxprep train gpt`

### 14d — 통합
- `voxprep train all` — sovits 완료 → gpt 실행

## ODP 관점

- `SovitsTrainConfig`, `GptTrainConfig` — Value Object (Phase 14a 이식 당시 이미 만들었던 것 재사용 가능)
- Trainer (`SovitsTrainer`, `GptTrainer`) — Service (모델+데이터+옵티마 묶음, 상태 있음)
- `WeightsPaths` — Value Object
- `train_sovits`/`train_gpt` Typer 커맨드 — 자유 함수 (어댑터)

## 의존성 추가

Phase 13의 torch/transformers 외에 추가로:
```bash
uv add pytorch-lightning tensorboard torchmetrics
```

## 완료 기준

- [ ] `uv run voxprep train all --exp-name e` 한 번에 SoVITS + GPT 학습 완료
- [ ] weights가 `voxprep/training/weights/SoVITS_weights_v2Pro/` 등에 저장 (또는 `--weights-root` 지정 경로)
- [ ] `voxprep/GPT-SoVITS/GPT_SoVITS/s{1,2}_train.py`, `module/`, `AR/` 삭제 가능
- [ ] Phase 13의 특징 추출 결과를 읽어 학습 시작

## 주의

- macOS MPS 불안정 → CPU 권장 (SETUP_GUIDE 5절)
- 장시간 실행 — Rich Live로 epoch/loss 실시간 표시 (Phase 11과 맞물림)
- batch_size 반감 (`is_half=False`일 때) 로직 이식 주의
- 체크포인트 포맷 호환: 이식된 trainer가 내는 pth/ckpt가 추론 단계(Phase 15)에서 그대로 로드돼야 함
