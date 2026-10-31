from vishlang.detect import ai_score

LLM = ("In today's rapidly evolving landscape, it is crucial to delve into the intricate "
       "tapestry of challenges. Furthermore, fostering a robust framework underscores the "
       "pivotal role of meticulous planning. Ultimately, this serves as a testament to resilience.")
HUMAN = ("ok so I looked at the thing again and honestly it's fine, the bug was just the "
         "cache key. pushed a fix, tell me if it still breaks for you tomorrow")
DASHY = "This works well — mostly — but there are caveats — several, in fact — worth noting."


def test_llm_text_scores_higher_than_human():
    assert ai_score(LLM) > ai_score(HUMAN)


def test_llm_text_above_threshold():
    assert ai_score(LLM) >= 0.5


def test_human_text_below_threshold():
    assert ai_score(HUMAN) < 0.5


def test_em_dash_density_pushes_score_up():
    assert ai_score(DASHY) > ai_score(HUMAN)


def test_bounds_and_empty():
    assert ai_score("") == 0.0
    assert 0.0 <= ai_score(LLM) <= 1.0
