from vishlang.blind import run_blind
from vishlang.llm import FakeLM

HOLD = [{"text": f"my text {i} is short and real enough honestly", "source": "gmail"} for i in range(4)]


def _lm():
    return FakeLM(lambda s, u: ("NEUTRAL " + u) if "generic AI assistant" in s else ("MINE " + u))


def test_run_blind_scores_scripted_answers():
    shown = []

    def ask(prompt):
        shown.append(prompt)
        return "1" if "1) MINE" in prompt else "2"

    r = run_blind(_lm(), HOLD, "rw-sys", n=4, ask=ask)
    assert r["hits"] == 4 and r["n"] == 4 and r["passed"] is True and len(shown) == 4
    assert r["ai_rewrite"] <= r["ai_neutral"] and r["len_ratio"] > 0


def test_run_blind_fails_below_threshold():
    r = run_blind(_lm(), HOLD, "rw-sys", n=4, ask=lambda p: "2" if "1) MINE" in p else "1")
    assert r["hits"] == 0 and r["passed"] is False


def test_run_blind_shows_both_versions_in_random_order():
    orders = set()

    def ask(prompt):
        orders.add("1) MINE" in prompt)
        return "1"

    run_blind(_lm(), HOLD, "rw-sys", n=4, ask=ask, rng_seed=3)
    assert orders == {True, False}
