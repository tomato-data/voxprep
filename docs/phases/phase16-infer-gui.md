# Phase 16 — 추론 tkinter GUI

## 사용자 시점

```bash
voxprep gui
```

### GUI 구성

- **모델 선택 드롭다운**: 사용 가능한 weights 자동 스캔
- **레퍼런스 오디오**: 파일 선택 다이얼로그 + 파형 미리보기
- **텍스트 입력 영역**: 여러 줄 입력 가능
- **추론 파라미터 슬라이더**: temperature, top_k, top_p, speed
- **생성 버튼 + 진행률 바**
- **결과 재생 + 저장**: 재생 버튼, "다른 이름으로 저장"

## 구현 전략

- tkinter + ttk (외부 의존성 없음)
- Phase 15의 `InferenceSession`을 그대로 사용 — GUI는 얇은 프론트엔드
- 추론은 별도 스레드에서 실행 (UI 블로킹 방지)
- 오디오 재생: `subprocess` (afplay/aplay) 또는 `simpleaudio`

## Phase 15와의 관계

GUI와 CLI가 같은 `InferenceSession`을 공유. 추론 로직 중복 없음.
