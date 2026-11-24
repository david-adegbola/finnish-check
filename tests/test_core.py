import json
from pathlib import Path

from core import batch, finnish, llm, rank

ROOT = Path(__file__).resolve().parent.parent
LIVE = llm.Settings(api_key="test-key")
MOCK = llm.Settings()


def fake_model(level, evidence):
    """Stands in for the API: returns a fixed answer."""
    return lambda system, user, schema, settings: {"data": {"level": level, "evidence": evidence,
                                                           "explanation_en": "x"}, "model": "test"}


def test_a_real_quote_is_kept():
    ad = "Kesäharjoittelija\nSuomen kielen taito katsotaan eduksi."
    result = finnish.classify(ad, LIVE, call=fake_model("preferred", ["Suomen kielen taito katsotaan eduksi."]))
    assert (result["level"], result["verified"]) == ("preferred", True)


def test_an_invented_quote_makes_the_result_unclear():
    ad = "Kesäharjoittelija\nSuomen kielen taito katsotaan eduksi."
    result = finnish.classify(ad, LIVE, call=fake_model("required", ["Fluent Finnish is required."]))
    assert result["level"] == "unclear"
    assert result["rejected_evidence"] == ["Fluent Finnish is required."]


def test_only_spaces_and_line_breaks_may_differ():
    ad = "Edellytämme   sujuvaa\nsuomen kielen taitoa."
    ok = finnish.classify(ad, LIVE, call=fake_model("required", ["Edellytämme sujuvaa suomen kielen taitoa."]))
    changed = finnish.classify(ad, LIVE, call=fake_model("required", ["Edellytämme sujuvaa suomen kielen taitoa!"]))
    assert (ok["level"], changed["level"]) == ("required", "unclear")


def test_a_level_without_a_quote_is_unclear():
    assert finnish.classify("Intern. Python.", LIVE, call=fake_model("not_needed", []))["level"] == "unclear"


def test_mock_mode_is_labelled_and_does_not_call_the_api():
    def no_api(*args):
        raise AssertionError("mock mode must not call the API")
    result = finnish.classify("Intern\nFinnish is an advantage.", MOCK, call=no_api)
    assert result["method"] == "mock"
    assert llm.MOCK_LABEL in result["explanation_en"]


def test_baseline_v1_and_its_known_mistake():
    assert finnish.baseline_v1("Edellytämme sujuvaa suomen kielen taitoa.") == "required"
    assert finnish.baseline_v1("Our working language is English.") == "not_required"
    assert finnish.baseline_v1("Hyvä suomen kielen taito on eduksi.") == "required"   # really "preferred"


def test_ranking_order():
    ads = [{"id": "a", "title": "A", "url": "", "ad_text": "Python and SQL."},
           {"id": "b", "title": "B", "url": "", "ad_text": "Python."},
           {"id": "c", "title": "C", "url": "", "ad_text": "Python and SQL."}]
    levels = {"a": {"level": "required"}, "b": {"level": "not_needed"}, "c": {"level": "preferred"}}
    assert [r["id"] for r in rank.rank(ads, ["Python", "SQL"], levels)] == ["b", "c", "a"]
    assert [r["id"] for r in rank.rank(ads, ["Python", "SQL"], levels, "fluent")] == ["a", "c", "b"]


def test_pasted_ads_are_split_on_dashes():
    parsed = batch.parse_pasted("First ad\ntext\n---\nSecond ad\n-----\n")
    assert [ad["title"] for ad in parsed["ads"]] == ["First ad", "Second ad"]


def test_api_request_shape():
    url, headers, body = llm.build_request(LIVE, "system", "user", finnish.SCHEMA, 100)
    assert url == llm.ANTHROPIC_URL
    assert headers["anthropic-version"] == "2026-10-21"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert "temperature" not in body           # rejected by the current models


def test_openrouter_is_used_when_its_key_is_set():
    settings = llm.settings_from_env({"OPENROUTER_API_KEY": "sk-or-test", "LLM_MODEL": "claude-haiku-5-5"})
    assert (settings.provider, settings.live) == ("openrouter", True)
    url, headers, body = llm.build_request(settings, "system", "user", finnish.SCHEMA, 100)
    assert url == llm.OPENROUTER_URL
    assert headers["authorization"] == "Bearer sk-or-test"
    assert body["model"] == "anthropic/claude-haiku-5.5"
    assert body["messages"][0] == {"role": "system", "content": "system"}
    assert body["response_format"]["json_schema"]["schema"] == finnish.SCHEMA
    assert body["provider"] == {"require_parameters": True, "data_collection": "deny"}
    assert "sk-or-test" not in repr(settings)


def test_openrouter_model_names():
    assert llm.openrouter_model("claude-opus-5-5") == "anthropic/claude-opus-5.5"
    assert llm.openrouter_model("claude-opus-5") == "anthropic/claude-opus-5"
    assert llm.openrouter_model("anthropic/claude-sonnet-5.5") == "anthropic/claude-sonnet-5.5"


def test_openrouter_reply_is_read_and_cut_off_answers_are_errors():
    import pytest
    settings = llm.Settings(provider="openrouter", api_key="sk-or-test")
    reply = {"model": "anthropic/claude-haiku-5.5",
             "choices": [{"finish_reason": "stop", "message": {"content": '{"level": "unclear"}'}}]}
    post = lambda url, headers, data, timeout: (200, {}, json.dumps(reply).encode())
    assert llm.call_json("s", "u", finnish.SCHEMA, settings, post=post)["data"] == {"level": "unclear"}
    reply["choices"][0]["finish_reason"] = "length"
    with pytest.raises(llm.LLMError):
        llm.call_json("s", "u", finnish.SCHEMA, settings, post=post)


def test_dataset_quotes_are_exact_and_sources_are_marked():
    rows = [json.loads(line) for line in (ROOT / "data" / "eval" / "ads.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert r["label"] in finnish.LEVELS
        if r["evidence"]:
            assert finnish.squash(r["evidence"]) in finnish.squash(r["ad_text_excerpt"]), r["id"]
        assert bool(r.get("invented")) == (r["source_url"] == ""), r["id"]


def test_evaluation_writes_nothing_when_an_api_call_fails(monkeypatch, tmp_path):
    import pytest
    from core import evaluate

    def failing(text, settings, call=None):
        raise llm.LLMError("Claude API call failed: HTTP 401 authentication_error.")
    monkeypatch.setattr(evaluate, "ROOT", tmp_path)
    (tmp_path / "data" / "eval").mkdir(parents=True)
    (tmp_path / "data" / "eval" / "ads.jsonl").write_text(
        (ROOT / "data" / "eval" / "ads.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(evaluate.finnish, "classify", failing)
    with pytest.raises(SystemExit):
        evaluate.main()
    assert not (tmp_path / "eval").exists()
