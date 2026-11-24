"""How much Finnish does a job ad ask for?

Levels: "required", "preferred" (an advantage), "not_needed", "unclear".

baseline_v1(text)
    The keyword rule from the author's earlier tool, JobDesk, copied unchanged. It answers only
    "required" or "not_required". It is kept so the evaluation can compare it with the LLM.

classify(ad_text, settings)
    Live mode: asks the LLM (prompt in prompts/finnish_level.md) for
        {"level", "evidence": [exact sentences from the ad], "explanation_en"}.
    Mock mode (no API key): a simple keyword guess, clearly labelled as mock output.
    Either way, check() then verifies the quotes (see below).

The quote check: a model can invent a convincing quote. check() keeps a result only if every
quoted sentence really appears in the ad (ignoring differences in spaces and line breaks, nothing
else). If any quote is not found, or a level other than "unclear" comes with no quote at all, the
result becomes "unclear".
"""

import re
from pathlib import Path

from core import llm

LEVELS = ("required", "preferred", "not_needed", "unclear")
PROMPT_FILE = Path(__file__).parent / "prompts" / "finnish_level.md"
PROMPT_VERSION = "finnish_level-v1"
MAX_AD_CHARS = 20_000

# JobDesk's "fluent Finnish" rule, character for character
BASELINE_V1_PATTERN = (r"sujuva\w* suome|hyvä\w* suomen kiel|erinomai\w* suomen kiel|fluent finnish|native finnish|"
                       r"suomen kielen taito on (?:edellytys|välttämätön)")

# The JSON shape the model must answer in (structured outputs)
SCHEMA = {
    "type": "object",
    "properties": {
        "level": {"type": "string", "enum": list(LEVELS)},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "explanation_en": {"type": "string"},
    },
    "required": ["level", "evidence", "explanation_en"],
    "additionalProperties": False,
}

SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")
FINNISH_MENTION = re.compile(r"suome|finnish|finska", re.I)
ADVANTAGE = re.compile(r"eduksi|etu\b|plussaa|advantage|a plus|nice to have|meriterande|toivomme", re.I)
NOT_NEEDED = re.compile(r"not (?:required|needed)|ei vaadita|ei ole välttämätön|working language is english|"
                        r"työkieli(?:mme)? on englanti", re.I)


def baseline_v1(text):
    """'required' when the old regex matches, else 'not_required'."""
    return "required" if re.search(BASELINE_V1_PATTERN, (text or "").lower()) else "not_required"


def squash(text):
    """Collapse runs of spaces and line breaks into one space."""
    return " ".join((text or "").split())


def verify_evidence(ad_text, evidence):
    """(found, not_found): which quotes really appear in the ad."""
    ad = squash(ad_text)
    found, missing = [], []
    for quote in evidence:
        if isinstance(quote, str) and squash(quote) and squash(quote) in ad:
            found.append(quote)
        else:
            missing.append(quote)
    return found, missing


def result(level, evidence, explanation, method, model="", rejected=()):
    return {"level": level, "evidence": list(evidence), "explanation_en": explanation, "method": method,
            "model": model, "verified": not rejected, "rejected_evidence": list(rejected)}


def check(ad_text, answer, method, model=""):
    """Apply the quote rules to a raw answer."""
    level = answer.get("level")
    evidence = answer.get("evidence")
    if level not in LEVELS or not isinstance(evidence, list):
        return result("unclear", [], "The answer was not in the expected form.", method, model)
    found, missing = verify_evidence(ad_text, evidence)
    if missing:
        return result("unclear", found, "The quoted text is not in the ad, so this result can't be trusted. "
                      "Read the ad's language requirements yourself.", method, model, rejected=missing)
    if level != "unclear" and not found:
        return result("unclear", [], "No sentence from the ad supports the answer.", method, model)
    return result(level, found, answer.get("explanation_en") or "", method, model)


def mock_answer(ad_text):
    """MOCK MODE ONLY: a crude keyword guess so the app can be tried without an API key. Labelled."""
    sentences = [s.strip() for s in SENTENCE.findall(ad_text or "") if s.strip()]
    for sentence in sentences:
        if NOT_NEEDED.search(sentence):
            return {"level": "not_needed", "evidence": [sentence],
                    "explanation_en": f"{llm.MOCK_LABEL} Keyword guess: the ad seems to say Finnish isn't needed."}
    for sentence in sentences:
        if FINNISH_MENTION.search(sentence):
            level = "preferred" if ADVANTAGE.search(sentence) else "required"
            return {"level": level, "evidence": [sentence],
                    "explanation_en": f"{llm.MOCK_LABEL} Keyword guess based on this sentence."}
    return {"level": "unclear", "evidence": [],
            "explanation_en": f"{llm.MOCK_LABEL} Keyword guess: the ad doesn't mention Finnish."}


def classify(ad_text, settings, call=None):
    """Classify one ad. call replaces llm.call_json in tests. Raises llm.LLMError if a live call fails."""
    text = (ad_text or "")[:MAX_AD_CHARS]
    if not text.strip():
        return result("unclear", [], "The ad has no text.", "none")
    if not settings.live:
        return check(text, mock_answer(text), "mock")
    reply = (call or llm.call_json)(PROMPT_FILE.read_text(encoding="utf-8"),
                                    f"<job_ad>\n{text}\n</job_ad>", SCHEMA, settings)
    return check(text, reply["data"], "llm", reply["model"])
