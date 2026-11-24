# How the code works, file by file

This is a walk-through of every file and function, in the order a request travels through the app.

## `app.py`: the Flask app

- **`load_dotenv(...)`**: reads `.env` (if there is one) into environment variables, so `ANTHROPIC_API_KEY` can live
  in a git-ignored file instead of the code.
- **`app.config["MAX_CONTENT_LENGTH"]`**: Flask refuses any request over 300 KB with error 413, before our code runs.
  `too_large()` turns that into the form page with a friendly message.
- **`read_ads(form, files)`**: if a CSV file was uploaded, checks the file name ends in `.csv`, decodes it as UTF-8
  (`utf-8-sig` also accepts the invisible "BOM" mark Excel adds) and passes it to `batch.parse_csv`. Otherwise it
  passes the text box to `batch.parse_pasted`.
- **`read_skills(text)`**: splits the skills box on commas and new lines, drops empty entries and duplicates
  (`dict.fromkeys` keeps the first of each, in order) and keeps at most 30.
- **`classify_all(ads, settings)`**: runs `finnish.classify` on every ad. In live mode a `ThreadPoolExecutor` sends up
  to 4 ads to the API at the same time, so 20 ads don't take 20 × the time of one. If one call fails, that ad becomes
  "unclear" with the reason, and the others still work. It returns `{ad id: result}`.
- **Routes**
  - `GET /` (`index`): shows the form.
  - `GET /samples` (`samples`): returns `data/samples.json` as JSON for the "Load sample ads" button.
  - `POST /analyze` (`analyze`): reads the ads, skills and Finnish level. With no usable ad it shows the form again
    with the errors (status 400). Otherwise: `classify_all` → `rank.rank` → `results.html`.
  - `GET /about` (`about`): reads `eval/summary.json` (written by the evaluation) for the numbers.

## `core/batch.py`: reading the ads

- **`parse_pasted(text)`**: splits on lines that contain only three or more dashes (the regex `^\s*-{3,}\s*$` with
  the multi-line flag), keeps the first `MAX_ADS` (20) blocks, and rejects blocks over `MAX_AD_CHARS` (10,000) with a
  message.
- **`parse_csv(text)`**: uses Python's `csv.DictReader`. It requires an `ad_text` column (`title` and `url` are
  optional), skips empty rows with a message, caps rows and length the same way, and catches `csv.Error` for broken
  files.
- **`make_ad(...)`**: builds `{"id", "title", "url", "ad_text"}`. The title is the given title or the first line.
- Both return `{"ads": [...], "errors": [...]}`, so one bad ad never stops the others.

## `core/finnish.py`: the classifier

- **`LEVELS`**: the four answers: required, preferred, not_needed, unclear.
- **`baseline_v1(text)`**: the regular expression from my earlier tool, JobDesk, unchanged. It is used only for
  comparison in the evaluation.
- **`SCHEMA`**: the JSON shape the model must answer in. The API enforces it ("structured outputs"): `level` must be
  one of the four, `evidence` a list of strings, `explanation_en` a string.
- **`classify(ad_text, settings)`**:
  - empty ad → "unclear";
  - mock mode → `mock_answer`;
  - live mode → sends the prompt file as the *system* message and the ad wrapped in `<job_ad>` tags as the *user*
    message, then passes the answer to `check`.
- **`check(ad_text, answer, method)`**: the safety net. It accepts the model's level only if (1) the level is one of
  the four, (2) every quoted sentence is found in the ad by `verify_evidence`, and (3) a level other than "unclear"
  has at least one quote. Otherwise the result is "unclear", with any rejected quote kept for transparency.
- **`verify_evidence(ad_text, evidence)`**: compares after `squash()`, which turns runs of spaces and line breaks
  into one space. Nothing else is forgiven: a changed letter or punctuation mark means "not found".
- **`mock_answer(ad_text)`**: used only without an API key. It finds the first sentence that says Finnish isn't
  needed, otherwise the first sentence mentioning Finnish, and calls it "preferred" if it contains an "advantage"
  word, otherwise "required". Every explanation starts with "[MOCK – not an AI result]".
- **`result(...)`**: builds the result dictionary in one place, so every path returns the same keys.

## `core/prompts/finnish_level.md`: the instructions to the model

It defines the four levels with typical Finnish, English and Swedish wording, lists the traps (an ad written in
Finnish doesn't by itself require Finnish; "hyvä suomen kielen taito … eduksi" is "preferred"), says the ad is data
and not instructions (against prompt injection), and states the evidence rules that `check()` enforces.

## `core/llm.py`: talking to Claude (directly or through OpenRouter)

- **`settings_from_env()`**: reads `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` (which one is set decides the
  `provider`), `LLM_MODEL`, `LLM_EFFORT` and `LLM_MODE`. `Settings.live` is true only when a key is set and mock mode
  isn't forced. The key is excluded from `repr()`, so it can't be printed by accident.
- **`openrouter_model(name)`**: turns Anthropic's model names into OpenRouter's (`claude-haiku-5-5` →
  `anthropic/claude-haiku-5.5`) with one regular expression; a name that already has a `/` is kept.
- **`build_request(...)`**: returns the URL, headers and JSON body for the chosen provider.
  - **Anthropic:** `x-api-key` and `anthropic-version: 2026-10-21` headers; `output_config` holds the effort and the
    JSON schema.
  - **OpenRouter:** an `Authorization: Bearer` header and OpenAI-style `messages`; `response_format` holds the JSON
    schema; `provider: {"require_parameters": true, "data_collection": "deny"}` means only providers that support
    the schema and don't store or train on the data may answer.

  It is separate so tests can check both requests without a network. There is no `temperature`: the current Claude
  models reject it.
- **`answer_text(...)`**: the two services shape their replies differently (`content` blocks vs `choices`). This
  function pulls out the JSON text, and treats a refusal or a cut-off answer as an error.
- **`call_json(...)`**: POSTs with `urllib` from the standard library. It retries on rate limits (429), server
  errors (5xx) and network errors, waiting `retry-after` seconds or 1, 2… seconds. It treats a refusal or a cut-off
  answer as an error, takes the text block and parses it as JSON. Error messages never contain the ad or the key.

## `core/rank.py`: the shortlist

- **`skill_matches(text, skills)`**: a skill counts when every significant word of it appears in the ad.
  "Significant" means not a stop word. Words are compared with `word_matches` from `core/text.py`, so Finnish case
  endings still match. One- and two-letter skills ("R") must match a whole word.
- **`rank(ads, skills, results, student_finnish)`**: gives each ad a tier from its Finnish level (not_needed 0,
  preferred 1, unclear 2, required 3; all 0 if the student is fluent) and a skill score (the share of the student's
  skills found). It sorts by tier, then score, then skills found in the title, and adds plain-English reasons.

## `core/text.py`: word helpers

- **`tokens(text)`**: lower-case words (letters, digits, å/ä/ö, inner hyphens).
- **`word_matches(word, keyword)`**: true if they are equal; or if the ad word starts with the skill word minus up to
  3 letters and adds at most 6 (Finnish endings: "paikkatieto" → "paikkatietoa"); or, for skill words of 6+ letters,
  if the skill word appears inside a longer compound ("asennus" in "sähköasennustyöt").

## `core/evaluate.py`: measuring accuracy

- **`load_dataset`**: reads `data/eval/ads.jsonl`, one labelled ad per line.
- **`scores(gold, predicted, labels)`**: accuracy, a confusion matrix (rows = true label, columns = prediction) and
  precision/recall per class.
- **`evaluate(...)`**: the four-level table for the classifier, and "collapsed" yes/no tables for both classifiers
  ("preferred" and "not_needed" count as "not required"; "unclear" ads are left out of the yes/no comparison).
- **`report(...)`** writes `eval/REPORT.md`, including every disagreement. **`main()`** runs it all and also writes
  `eval/summary.json` for the /about page.

## Templates, CSS and JavaScript

- `base.html`: header, the yellow mock-mode banner, footer with the privacy line.
- `index.html`: the form. `results.html`: the table; each row has `data-level` so the filter can hide "required" rows.
- `about.html`: problem, method, numbers from `summary.json`, limitations, privacy.
- `style.css`: colours defined once at the top; every badge has a text label, so colour isn't the only signal.
- `app.js`: two event handlers. "Load sample ads" fetches `/samples` and fills the text box. The checkbox adds or
  removes a `hidden` class on rows with `data-level="required"`.

## Data and tests

- `data/samples.json`: 10 sample ads (6 real excerpts with source links, 4 invented, marked).
- `data/eval/ads.jsonl` + `GUIDE.md`: 38 labelled ads and the labelling rules.
- `tests/test_app.py`: pages return 200, mock mode works end to end, empty input and too many ads, CSV upload and
  validation, the filter, and that live mode uses the classifier (with a fake classifier, no network).
- `tests/test_core.py`: the quote check (real quote kept, invented quote rejected, only whitespace may differ),
  mock labelling, `baseline_v1`'s known mistake, ranking order, pasted-ad splitting, the API request shape, and
  that every quote in the dataset is really in its excerpt.
