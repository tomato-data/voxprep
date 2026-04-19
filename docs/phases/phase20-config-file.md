# Phase 20 — 기본값 설정 파일 + CLI 오버라이드 체계

## 배경

voxprep의 커맨드들(slice/asr/prep/extract/train/infer)은 업스트림이 노출하는 모든 노브를 CLI 플래그로 제공합니다. 이는 SETUP_GUIDE의 의도("설정 노브는 모두 CLI에") 그대로이지만, 실사용에서 다음 마찰이 생겼습니다:

- **매번 같은 플래그 반복** — `--sample-rate 44100 --version v2Pro --language ko` 등을 매 세션마다 다시 입력
- **프로젝트/데이터셋별 기본값 차이** — 스튜디오 내레이션과 실황 강연은 `--threshold`, `--min-length`, `--vad-min-silence-ms` 등이 달라짐
- **스크립트화의 부담** — shell alias 또는 래퍼 스크립트에 파편화됨

## 해결 방향

사용자가 **한 번 설정하고 여러 번 실행**할 수 있는 config 파일 체계를 도입합니다.

### 우선순위 체인

```
CLI --flag  >  VOXPREP_CONFIG env var-pointed file  >  ./voxprep.toml  >  ~/.config/voxprep/config.toml  >  내장 기본값 (SETUP_GUIDE)
```

왼쪽으로 갈수록 우선. CLI 플래그는 언제나 최종 오버라이드.

### 포맷 — TOML

```toml
# ~/.config/voxprep/config.toml

[global]
models_root = "/Users/me/voxprep-models"
version = "v2Pro"

[slice]
sample_rate = 44100
threshold = -34
min_length = 4000

[asr]
language = "ko"
model_size = "large-v3-turbo"
vad = true

[train]
batch_size = 1
save_every = 4
sovits_epochs = 12
gpt_epochs = 20

[infer]
autoselect = true
no_play = false
```

커맨드별 섹션 (`[slice]`, `[asr]`, `[train]`, `[infer]`) + 공통 `[global]`. TOML을 쓰는 이유: Python 3.11+ 표준 `tomllib`, pyproject.toml과 친숙, 주석 지원.

## 구현 범위

### 20a — Config 모델 + 로더
- `src/voxprep/config.py` 신설
- `@dataclass(frozen=True)` 기반 `VoxprepConfig`, `SliceDefaults`, `AsrDefaults`, `TrainDefaults`, `InferDefaults`
- `load_config(explicit_path=None) -> VoxprepConfig` — 우선순위 체인 해석
- 누락 필드는 SETUP_GUIDE 기본값으로 채움 (named constructor)

### 20b — CLI 통합
- 각 `commands/*.py` 가 함수 시작부에서 `config = load_config()` 호출
- Typer `Option(default=...)` 를 `Option(None)`으로 바꾸고, None 이면 config 값 사용
  - 패턴: `sample_rate: int = typer.Option(None, ...)` → `sample_rate or config.slice.sample_rate`
- 공통 헬퍼 `_resolve_option(cli_value, config_value, builtin_default)`

### 20c — `voxprep config` 서브커맨드
- `voxprep config show` — 현재 해석된 config 출력 (어느 소스에서 왔는지 표시)
- `voxprep config init [--global | --local]` — 기본 config 파일 생성
- `voxprep config edit` — 기본 에디터로 config 열기 (`$EDITOR`)
- `voxprep config path` — 우선순위별 config 파일 경로 + 존재 여부

### 20d — 문서
- `docs/GUIDE.md` 에 config 파일 섹션 추가
- README 에 Highlight 반영

## ODP 관점

| 객체 | 분류 | 메모 |
|------|------|------|
| `VoxprepConfig` | Value Object | frozen dataclass, 전체 config 스냅샷 |
| `SliceDefaults`, `AsrDefaults`, `TrainDefaults`, `InferDefaults` | Value Object | 섹션별 타입 |
| `ConfigSource` | Enum | CLI / EXPLICIT_FILE / LOCAL / USER / BUILTIN |
| `load_config` | 자유 함수 | 우선순위 체인 해석 |
| `ResolvedOption[T]` | Value Object (선택) | `(value: T, source: ConfigSource)` — `config show` 에서 소스 추적 용 |

## 테스트 전략

- `tests/unit/test_config.py`
  - 빈 파일 → SETUP_GUIDE 기본값
  - 부분 섹션 → 누락 필드만 기본값
  - CLI 오버라이드 우선순위
  - 잘못된 포맷 → `InvalidConfig` 예외 (Phase 19의 도메인 예외 패턴 활용)
- `tests/integration/test_config_cli.py`
  - `voxprep config init` → 파일 생성 확인
  - `voxprep config show` → 소스별 출력
  - Config 파일로 `voxprep prep` 기본값 바뀌는지 e2e

## 완료 기준

- [ ] 20a: `load_config()` 구현 + 단위 테스트 통과
- [ ] 20b: 기존 CLI 커맨드가 config 값을 읽어들이는지 검증
- [ ] 20c: `voxprep config show/init/edit/path` 동작
- [ ] 20d: GUIDE.md 갱신, README 반영
- [ ] 기존 73+ 테스트 회귀 없음
- [ ] 커밋:
  - `feat: add VoxprepConfig VOs and load_config`
  - `feat: resolve CLI options from config file with override chain`
  - `feat: add voxprep config subcommand`
  - `docs: document config file support`

## 주의

- **Phase 19(ODP 정제) 이후가 자연스러움** — VO 검증 강화·도메인 예외 정비가 끝난 뒤 Config VO들을 그 관례 위에 올리면 일관성 유지
- **호환성** — 기존 사용자의 CLI 플래그 스크립트는 전부 그대로 동작 (config 파일 없으면 기존 동작)
- **민감 경로 금지** — config 파일에 절대 비밀번호/토큰 같은 것 담지 말 것 (현재는 해당 없지만 향후 API 키 등 추가 시 주의)
