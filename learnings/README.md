# learnings

voxprep(GPT-SoVITS 전처리 CLI) 학습 프로젝트의 **진짜 산출물**이 쌓이는 자리입니다. `docs/`(Claude가 준 Phase 지시서)와 대칭으로, 여기엔 **내가 질문하고 내가 답을 받은 내용**, **내가 겪은 시행착오**, **Phase 끝의 회고**가 쌓입니다. 코드는 부산물이고 이 디렉토리가 본체라고 여기고 성실하게 채웁니다.

## 파일 구성 (플랫 모드, ≤10 Phase)

Phase당 두 종류의 파일:

- `phaseNN-qa.md` — Phase 진행 중 **내가 던진 질문**과 답변 (섹션: TDD / ODP / Python / Typer·CLI / 리라이트 전략)
- `phaseNN-{topic}.md` — Phase 완료 시 회고. `topic`은 그 Phase의 핵심 개념·깨달음을 한 단어로 압축

Phase 경계를 가로지르는 글로벌 파일:

- [`DISCOVERIES.md`](DISCOVERIES.md) — **묻지 않았지만 튀어나와 배우게 된 것들**의 누적 로그. 디버깅 중 마주친 함정, 프레임워크 내부 동작, 허위 GREEN 위험, 잘못 이해한 가정 등. Q&A와 성격이 다름(질문 vs 발견)

## Phase별 학습 맵

| Phase | 주제 | Q&A | 회고 | 배운 것 (2줄) |
|---|---|---|---|---|
| 01 | 부트스트랩 — Typer + pytest | [phase01-qa.md](phase01-qa.md) | (pending) | — |
| 02 | `.list` 파서 | (pending) | (pending) | — |
| 03 | `slice` 커맨드 | (pending) | (pending) | — |
| 04 | `asr` 커맨드 | (pending) | (pending) | — |
| 05 | `review` — 내비게이션 | (pending) | (pending) | — |
| 06 | `review` — 오디오 재생 | (pending) | (pending) | — |
| 07 | `review` — 인라인 편집 | (pending) | (pending) | — |
| 08 | `review` — 삭제 + undo | (pending) | (pending) | — |
| 09 | `review` — 자동 플래그 | (pending) | (pending) | — |
| 10 | `prep` 올인원 파이프라인 | (pending) | (pending) | — |

## 작성 규칙

- **Q&A는 Phase 진행 중 즉시 기록**. 질문이 떠오를 때 → Claude에게 묻기 → 답을 받은 뒤 해당 Phase의 `phaseNN-qa.md`에 붙여넣기. 나중에 몰아서 쓰면 맥락이 날아감
- **회고는 Phase 완료 시 한 번에**. 감상 + 가장 인상적이었던 한 가지 + 다음 Phase로 가져갈 것을 짧게라도 남기기
- 형식은 자유지만 **섹션 헤더**는 유지: `## TDD 개념`, `## ODP`, `## Python`, `## Typer/CLI`, `## 리라이트 전략` 등. 나중에 vault로 승격할 때 분류 편해짐

## 승격 경로

프로젝트 종료 후 이 디렉토리는 `200 Dev KB/{도메인}/voxprep-study/`로 아카이브되고, 주제별 내용은 Dev KB의 카테고리로 분산 승격됩니다. 위 학습 맵 표가 그 매핑 초안이 됩니다 — 그래서 "2줄 요약"을 성실히 채울수록 나중이 쉬워집니다.
