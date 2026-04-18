# voxprep — Phase 로드맵

GPT-SoVITS의 전처리 → 학습 → 추론 파이프라인을 CLI로 다시 짜는 프로젝트. TDD + ODP로 체화하면서, 실제로 돌아가는 CLI를 끝까지 가져갑니다.

## 전체 흐름

```
[video/audio] ──to-wav──▶ [raw wav]
                              │
                          prep ▼ (올인원)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
           [slice]         [asr]          [review]
           chunks/      draft.list      final.list
              │               │               │
              └───────────────┼───────────────┘
                              │
                        extract ▼ (특징 추출)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          1-get-text    2-get-hubert    3-get-semantic
          BERT 임베딩    HuBERT+32kHz    시맨틱 토큰
              │               │               │
              └───────────────┼───────────────┘
                              │
                          train ▼
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               SoVITS 학습          GPT 학습
               .pth weights        .ckpt weights
                    │                   │
                    └─────────┬─────────┘
                              │
                          infer ▼
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               CLI 세션             tkinter GUI
            (LLM tool use 연계)    (독립 앱)
```

## Phase 인덱스

### Part A — 데이터셋 전처리 (완료)

| # | 파일 | 제목 | 산출 커맨드 | 상태 |
|---|------|------|------------|------|
| 01 | [phase01-bootstrap.md](phases/phase01-bootstrap.md) | 부트스트랩 — Typer + pytest | `voxprep version` | ✅ |
| 02 | [phase02-list-parser.md](phases/phase02-list-parser.md) | `.list` 파서 (Value Object) | (라이브러리) | ✅ |
| 03 | [phase03-slice.md](phases/phase03-slice.md) | `slice` 커맨드 | `voxprep slice` | ✅ |
| 04 | [phase04-asr.md](phases/phase04-asr.md) | `asr` 커맨드 (faster-whisper) | `voxprep asr` | ✅ |
| 05 | [phase05-review-nav.md](phases/phase05-review-nav.md) | `review` — 내비게이션 | `voxprep review` (n/b/q) | ✅ |
| 06 | [phase06-review-playback.md](phases/phase06-review-playback.md) | `review` — 오디오 재생 | `voxprep review` (Enter) | ✅ |
| 07 | [phase07-review-edit.md](phases/phase07-review-edit.md) | `review` — 인라인 편집 | `voxprep review` (e) | ✅ |
| 08 | [phase08-review-delete-undo.md](phases/phase08-review-delete-undo.md) | `review` — 삭제 + undo | `voxprep review` (d/u) | ✅ |
| 09 | [phase09-review-flags.md](phases/phase09-review-flags.md) | `review` — 자동 플래그 | `--auto-prune` | ✅ |
| 10 | [phase10-prep-pipeline.md](phases/phase10-prep-pipeline.md) | `prep` 올인원 파이프라인 | `voxprep prep` | ✅ |

### Part B — UX 개선 + 유틸리티

| # | 파일 | 제목 | 산출 커맨드 | 상태 |
|---|------|------|------------|------|
| 11 | [phase11-progress-feedback.md](phases/phase11-progress-feedback.md) | Rich 진행률 표시 | (전체 커맨드 개선) | ⏳ |
| 12 | [phase12-to-wav.md](phases/phase12-to-wav.md) | `to-wav` — 영상→WAV 추출 | `voxprep to-wav` | ⏳ |
| 18 | [phase18-review-unified-filter.md](phases/phase18-review-unified-filter.md) | `review` 루프 통합 (auto-prune에 풀 UI) | `voxprep review --auto-prune` | ⏳ |

### Part C — 특징 추출 + 학습

| # | 파일 | 제목 | 산출 커맨드 | 상태 |
|---|------|------|------------|------|
| 13 | [phase13-extract.md](phases/phase13-extract.md) | `extract` — 특징 추출 파이프라인 | `voxprep extract` | ⏳ |
| 14 | [phase14-train.md](phases/phase14-train.md) | `train` — SoVITS + GPT 학습 | `voxprep train` | ⏳ |

### Part D — 추론

| # | 파일 | 제목 | 산출 커맨드 | 상태 |
|---|------|------|------------|------|
| 15 | [phase15-infer-cli.md](phases/phase15-infer-cli.md) | `infer` — CLI 대화형 추론 세션 | `voxprep infer` | ⏳ |
| 16 | [phase16-infer-gui.md](phases/phase16-infer-gui.md) | 추론 — tkinter GUI | (독립 앱) | ⏳ |
| 17 | [phase17-infer-api.md](phases/phase17-infer-api.md) | 추론 — LLM tool use 연계 | (API/서버) | ⏳ |

상태 표기: ⏳ pending · 🔵 in_progress · ✅ completed

## Phase 문서 읽는 법

각 Phase 문서는 다음 섹션으로 구성됩니다:

1. **학습 목표** — 이 Phase가 끝나면 무엇을 체화한 상태여야 하는가
2. **참조 자료** — `voxprep/GPT-SoVITS/` 또는 `claude-code-study/`에서 어떤 파일을 읽을지
3. **구현 범위** — 무엇을 새로 만드는가, 무엇은 다음 Phase로 미루는가
4. **TDD 사이클 시나리오** — RED → GREEN → REFACTOR 흐름과 각 단계의 테스트/스니펫 윤곽
5. **ODP 관점** — 등장하는 객체들의 분류와 그 이유
6. **파일 구조** — 새로 생성/수정할 파일과 그 책임
7. **완료 기준** — 다음 Phase로 넘어가기 위한 체크리스트
8. **주의사항 / 엣지케이스** — 알고 넘어가야 할 함정들

## 작업 규칙 요약

- **튜터 모드**: Claude는 학습 대상 코드(`src/`, `tests/`)를 직접 작성하지 않고 스니펫만 보여줍니다. 사용자가 직접 타이핑.
- **인프라/메타 파일 예외**: `.gitignore`, `pyproject.toml`, `CLAUDE.md`, `docs/**/*.md`는 Claude가 직접 작성 OK.
- **도메인 알고리즘 예외**: 음성 처리/DSP/GPT-SoVITS 이식 코드는 Claude가 스니펫 제공 또는 직접 작성 OK.
- **TDD 사이클 분리 커밋**: GREEN 직후 REFACTOR는 별도 커밋. `feat:` / `refactor:` / `test:` 분리.

## GPT-SoVITS 디렉토리 원칙 ⚠️

- `voxprep/GPT-SoVITS/`는 **참고 전용** (.gitignore). 런타임에 절대 참조하지 않음
- Part C/D(특징 추출/학습/추론)는 해당 디렉토리에서 **코드를 voxprep 안으로 이식(copy + adapt)** 하는 작업
- 이식 완료 부분은 `voxprep/GPT-SoVITS/`에서 삭제 → 최종적으로 이 디렉토리는 비어야 함
- subprocess로 외부 스크립트 호출 금지

상세 작업 규칙은 루트 `CLAUDE.md` 참조.
