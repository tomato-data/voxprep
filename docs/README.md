# voxprep — Phase 로드맵

GPT-SoVITS 데이터셋 전처리 CLI(`slice` → `asr` → `review` → `prep`)를 TDD + ODP로 다시 짜는 학습 프로젝트의 Phase 인덱스입니다. 각 Phase 문서는 새 세션에서 그대로 프롬프트로 들어가도 충분히 이해하고 사용자에게 다음 행동을 요구할 수 있는 수준으로 작성되어 있습니다.

## 전체 흐름

```
[raw audio] ──slice──▶ [chunks] ──asr──▶ [draft .list] ──review──▶ [final .list]
                                                                       │
                                                                  prep ▼ (올인원)
                                                              학습 직전 데이터셋
```

## Phase 인덱스

| # | 파일 | 제목 | 산출 커맨드 | 상태 |
|---|------|------|------------|------|
| 01 | [phase01-bootstrap.md](phases/phase01-bootstrap.md) | 부트스트랩 — Typer + pytest | `voxprep version` | ⏳ |
| 02 | [phase02-list-parser.md](phases/phase02-list-parser.md) | `.list` 파서 (Value Object) | (라이브러리) | ⏳ |
| 03 | [phase03-slice.md](phases/phase03-slice.md) | `slice` 커맨드 | `voxprep slice` | ⏳ |
| 04 | [phase04-asr.md](phases/phase04-asr.md) | `asr` 커맨드 (faster-whisper) | `voxprep asr` | ⏳ |
| 05 | [phase05-review-nav.md](phases/phase05-review-nav.md) | `review` — 내비게이션 | `voxprep review` (n/b/q) | ⏳ |
| 06 | [phase06-review-playback.md](phases/phase06-review-playback.md) | `review` — 오디오 재생 | `voxprep review` (Enter) | ⏳ |
| 07 | [phase07-review-edit.md](phases/phase07-review-edit.md) | `review` — 인라인 편집 | `voxprep review` (e) | ⏳ |
| 08 | [phase08-review-delete-undo.md](phases/phase08-review-delete-undo.md) | `review` — 삭제 + undo | `voxprep review` (d/u) | ⏳ |
| 09 | [phase09-review-flags.md](phases/phase09-review-flags.md) | `review` — 자동 플래그 | `--auto-prune` | ⏳ |
| 10 | [phase10-prep-pipeline.md](phases/phase10-prep-pipeline.md) | `prep` 올인원 파이프라인 | `voxprep prep` | ⏳ |

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
- **TDD 사이클 분리 커밋**: GREEN 직후 REFACTOR는 별도 커밋. `feat:` / `refactor:` / `test:` 분리.
- **언제 GPT-SoVITS 파일을 지울까**: 해당 Phase 완료 + 회고 작성 후 `voxprep/GPT-SoVITS/`에서 리라이트 끝난 파일 삭제.

상세 작업 규칙은 루트 `CLAUDE.md` 참조.
