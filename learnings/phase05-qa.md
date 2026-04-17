# Phase 05 — Q&A

Phase 05(`review` 내비게이션 — Entity, 키바인딩 dispatcher, 입력 루프) 진행 중 주고받은 질문과 답변.

---

## 패턴/설계

### Q: Dispatcher의 영어 뜻은 뭐고, 코드에서의 의미는?

**Dispatch**의 영어 원뜻은 **"보내다, 파견하다"**. 택시 회사의 dispatcher는 "이 손님은 3번 차로, 저 손님은 7번 차로" 배분하는 사람.

코드에서의 dispatcher도 같다:

```
입력(키 "n")이 들어온다
    → dispatcher가 "n은 누구 담당이지?" 하고 찾는다
    → 등록된 액션(session.next)을 호출한다 = "파견"
```

**dispatcher는 "무엇을 할지" 결정하지 않는다.** "누가 할지"를 찾아서 연결해 줄 뿐. 내부 구조는 `dict[str, Callable]` — 키 문자열 → 콜백 함수 매핑.

dispatch가 없으면 키가 늘어날 때마다 `if/elif` 체인이 길어지지만, dispatch가 있으면 **루프 코드는 `outcome = dispatcher.handle(key, session)` 한 줄 그대로**이고 새 키는 `register()`로 등록만 추가하면 됨. "분기(if/elif)를 데이터(dict)로 바꾼 것"의 가장 작은 사례.

이 패턴은 이름만 바뀌어서 어디에나 있다:

| 도메인 | dispatch의 모양 |
|---|---|
| 웹 프레임워크 (FastAPI, Django) | URL → handler 함수 매핑 |
| 이벤트 시스템 | 이벤트 타입 → listener 함수 매핑 |
| CLI 프레임워크 (Typer/Click) | 서브커맨드 이름 → 커맨드 함수 매핑 |

Typer의 `app.command(name="slice")(slice_command)`도 "slice라는 키를 slice_command 함수에 등록하는 dispatcher". voxprep의 `Dispatcher`는 그걸 키보드 입력 버전으로 축소한 것.

---
