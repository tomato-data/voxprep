from voxprep.review.keybindings import Dispatcher, ReviewOutcome


def test_dispatcher_invokes_registered_actions():
    calls = []
    dispatcher = Dispatcher()
    dispatcher.register("n", lambda s: (calls.append("n"), ReviewOutcome.CONTINUE)[1])

    outcome = dispatcher.handle("n", session=None)

    assert calls == ["n"]
    assert outcome == ReviewOutcome.CONTINUE


def test_dipatcher_ignores_unknown_key():
    dispatcher = Dispatcher()

    assert dispatcher.handle("z", session=None) == ReviewOutcome.CONTINUE


def test_quit_action_returns_quit_outcome():
    dispatcher = Dispatcher()
    dispatcher.register("q", lambda s: ReviewOutcome.QUIT)

    assert dispatcher.handle("q", session=None) == ReviewOutcome.QUIT