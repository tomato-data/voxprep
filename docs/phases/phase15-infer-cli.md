# Phase 15 — `infer` CLI 대화형 추론 세션 (이식)

## 기본 방침

Phase 13/14와 동일. 추론 코드를 voxprep 안으로 **이식**. `voxprep/GPT-SoVITS/` 참조 금지.

## 이식 대상

| 원본 | voxprep 경로 | 설명 |
|------|-------------|------|
| `GPT_SoVITS/inference_webui.py`의 `get_tts_wav` | `src/voxprep/inference/synthesizer.py` | 핵심 추론 함수 |
| `GPT_SoVITS/module/models.py`의 Generator (추론 부분) | `src/voxprep/inference/sovits.py` | VQ → mel |
| `GPT_SoVITS/AR/` (추론 경로) | `src/voxprep/inference/gpt.py` | 자기회귀 추론 |
| Vocoder (v3/v4) | `src/voxprep/inference/vocoder.py` | mel → waveform |
| `GPT_SoVITS/TTS_infer_pack/` | `src/voxprep/inference/pack/` | 추론 파이프라인 래퍼 |


## 사용자 시점

```bash
voxprep infer
```

### 세션 흐름

```
$ voxprep infer

Available models:
  [1] myvoice_v1 (SoVITS: e10, GPT: e20)
  [2] demo_v1 (SoVITS: e8, GPT: e15)

Select model [1]: 1
Reference audio: ./ref/sample.wav
Reference text: 안녕하세요, 저는 테스트입니다.
Reference language [ko]: ko

Model loaded. Type text to synthesize (Ctrl+C to exit).

> 오늘 날씨가 정말 좋네요.
[생성 중...] ████████████ 100%
Playing: /tmp/voxprep_out_001.wav

> 다음 문장도 해볼게요.
[생성 중...] ████████████ 100%
Playing: /tmp/voxprep_out_002.wav
```

### 핵심 기능

1. **모델 선택**: weights 디렉토리를 스캔하여 사용 가능한 모델 목록 표시
2. **레퍼런스 설정**: 참조 오디오(3~10초) + 해당 텍스트 + 언어
3. **대화형 루프**: 텍스트 입력 → 추론 → 자동 재생 (afplay/aplay)
4. **출력 저장**: 생성된 wav를 자동 저장 (번호 자동 증가)

## 구현 전략

- GPT-SoVITS의 `get_tts_wav()` 함수를 in-process 호출
- 모델 로딩은 세션 시작 시 1회 (무거움)
- prompt_toolkit으로 입력 루프 (히스토리, 자동완성)
- 추론 파라미터: `top_k=20`, `top_p=0.6`, `temperature=0.6`, `speed=1` (SETUP_GUIDE 기본)

## LLM tool use 연계 (Phase 17 준비)

CLI 세션과 별개로, **프로그래밍 방식 호출이 가능한 인터페이스**를 함께 설계:

```python
from voxprep.inference import InferenceSession

session = InferenceSession(
    sovits_weights="path/to/sovits.pth",
    gpt_weights="path/to/gpt.ckpt",
    ref_audio="path/to/ref.wav",
    ref_text="참조 텍스트",
    ref_language="ko",
)
wav_path = session.synthesize("합성할 텍스트", language="ko")
```

이 인터페이스를 Phase 17에서 MCP tool / function calling으로 노출.

## 의존성

- GPT-SoVITS 추론 코드 (in-process import)
- 사전훈련 모델 + 파인튜닝된 weights
- 오디오 재생: `afplay` (macOS) / `aplay` (Linux)
