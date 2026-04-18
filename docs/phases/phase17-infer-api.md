# Phase 17 — 추론 LLM tool use 연계

## 목표

Local LLM의 tool use로 voxprep 추론을 호출하여, LLM 대답을 바로 음성으로 들을 수 있는 구조.

## 아키텍처

```
[Local LLM] ──tool call──▶ [voxprep inference server] ──wav──▶ [오디오 재생]
                                      │
                                      ▼
                              InferenceSession
                            (Phase 15에서 구현)
```

### 방법 1: MCP Server

```json
{
  "name": "synthesize_speech",
  "description": "텍스트를 음성으로 변환",
  "parameters": {
    "text": "합성할 텍스트",
    "language": "ko",
    "speaker": "myvoice"
  }
}
```

Claude Code / 기타 MCP 클라이언트에서 바로 호출 가능.

### 방법 2: REST API (상시 서버)

```bash
voxprep serve --port 9880
```

- GPT-SoVITS의 `api_v2.py`를 참조한 FastAPI 서버
- `POST /tts` → WAV 스트리밍 응답
- `POST /set-model` → 모델 교체
- 모델을 메모리에 유지하여 첫 호출 이후 빠른 응답

### 방법 3: 함수 직접 호출

```python
from voxprep.inference import InferenceSession

# LLM 에이전트 코드 내에서
session = InferenceSession(...)
wav_path = session.synthesize(llm_response_text)
subprocess.run(["afplay", wav_path])
```

## 의존성

- Phase 15 `InferenceSession` (핵심)
- MCP SDK 또는 FastAPI (서버 방식에 따라)
- Local LLM 런타임 (ollama, llama.cpp 등 — voxprep 범위 외)

## 구현 순서 권장

1. Phase 15 (InferenceSession) 완성이 선행
2. REST API 서버 (`voxprep serve`) 먼저 — 범용적
3. MCP Server는 그 위에 래핑
