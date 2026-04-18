# Phase 14 — `train` SoVITS + GPT 학습

## 사용자 시점

```bash
# 기본 (SETUP_GUIDE 검증값)
voxprep train --exp-name myvoice_v1

# 커스텀
voxprep train --exp-name myvoice_v1 \
  --sovits-epochs 10 \
  --gpt-epochs 20 \
  --batch-size 1 \
  --save-every 4
```

## 배경

2단계 학습: **SoVITS(s2) 먼저 → GPT(s1) 다음**.

### SoVITS 학습
- 입력: 특징 추출 결과 (`logs/{exp_name}/` 하위)
- 출력: `SoVITS_weights_{version}/{exp_name}-e{epoch}.pth`
- 설정: config JSON 템플릿에서 동적 생성
- 사전훈련 가중치 기반 파인튜닝

### GPT 학습
- 입력: 특징 추출 결과 + 시맨틱 토큰
- 출력: `GPT_weights_{version}/{exp_name}-e{epoch}.ckpt`
- 설정: config YAML 템플릿에서 동적 생성
- PyTorch Lightning 기반

## 구현 전략

- 원본 `s2_train.py`, `s1_train.py`를 **subprocess로 호출**
- config 템플릿을 읽어 사용자 옵션을 주입 후 임시 파일로 전달
- 학습 진행 상황: subprocess stdout 파싱 → Rich Live로 epoch/loss 표시
- macOS 주의: CPU 학습 권장 (MPS 불안정), 장시간 소요

## 기본값 (SETUP_GUIDE 검증)

- batch_size: 1
- sovits_epochs: 10
- gpt_epochs: 20 (또는 10)
- save_every: 4 epochs
- version: v2Pro
