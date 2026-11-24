# Evaluation report

Date: 2026-11-24 · Classifier mode: **mock**
 · Ads: 38 (30 real excerpts, 8 invented)

> **Mock mode:** the classifier column is the app's keyword guess, not the LLM. The guess was written after seeing these ads, so its score is not a fair result; it is shown only so the report format can be checked. Run with ANTHROPIC_API_KEY set for real LLM numbers.

## Collapsed: required vs not required

Preferred and not_needed count as not_required; 11 ads labelled unclear are left out.

### baseline_v1 (JobDesk's keyword rule), all ads

Accuracy: **59%** (16 of 27)

| true label \ predicted | required | not_required |
|---|---|---|
| required | 9 | 10 |
| not_required | 1 | 7 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 90% | 47% | 19 |
| not_required | 41% | 88% | 8 |

### baseline_v1, real ads only

Accuracy: **47%** (9 of 19)

| true label \ predicted | required | not_required |
|---|---|---|
| required | 8 | 10 |
| not_required | 0 | 1 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 100% | 44% | 18 |
| not_required | 9% | 100% | 1 |

### Classifier (mock), all ads

Accuracy: **78%** (21 of 27)

| true label \ predicted | required | not_required | unclear |
|---|---|---|---|
| required | 15 | 3 | 1 |
| not_required | 0 | 6 | 2 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 100% | 79% | 19 |
| not_required | 67% | 75% | 8 |

## Four levels (classifier only)

### Classifier (mock)

Accuracy: **76%** (29 of 38)

| true label \ predicted | required | preferred | not_needed | unclear |
|---|---|---|---|---|
| required | 15 | 3 | 0 | 1 |
| preferred | 0 | 3 | 1 | 1 |
| not_needed | 0 | 0 | 2 | 1 |
| unclear | 2 | 0 | 0 | 9 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 88% | 79% | 19 |
| preferred | 50% | 60% | 5 |
| not_needed | 67% | 67% | 3 |
| unclear | 75% | 82% | 11 |

## Disagreements

**real-0** – [source](https://valtiolle.fi/fi/tyopaikat/harjoittelija-ratasuunnittelun-tehtavat-helsinki-tampere-26709/)
- Label: **required** · baseline_v1: required · classifier: preferred ✗
- Evidence: “Tehtävässä menestyäkseen odotetaan hyvää suomen kielen taitoa ja eduksi luetaan tyydyttävä ruotsin kielen taito.”
- Note: 'odotetaan' (expected) for success; treated as a requirement

**real-1** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-viestinta-vaasa-26546/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Hyvä suomen ja ruotsin kielten taito.”
- Note: listed under the requirements

**real-3** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-mediakasvatustehtaviin-26557/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Työtehtävät edellyttävät erinomaista suullista ja kirjallista suomen kielen taitoa.”


**real-4** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-2-kpl-26102/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Tehtävässä tarvitaan hyvää suullista ja kirjallista suomen kielen taitoa sekä tyydyttävää ruotsin kielen suullista ja kirjallista taitoa.”
- Note: tricky: the same ad says there are no formal language requirements, then that good Finnish is needed

**real-6** – [source](https://valtiolle.fi/fi/tyopaikat/harjoittelija-visuaalinen-viestinta-helsinki-26521/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: preferred ✗
- Evidence: “Suomen kielen taitosi on erinomainen, englannin ja ruotsin taidot sekä hyvä kirjallinen ilmaisu ovat eduksi.”
- Note: word order defeats the old regex

**real-7** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-lupapalveluyksikko-26564/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Korkeakouluharjoittelijalta edellytämme hyvää suomen ja käytännön ruotsin ja englannin kielen taitoa.”
- Note: 'suomen ja ... kielen' defeats the old regex

**real-11** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-vaalitiimi-26446/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Tehtävä edellyttää erinomaista suullista ja kirjallista suomen kielen taitoa sekä tyydyttävää ruotsin kielen suullista taitoa.”


**real-12** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-osint-kehitys-2-paikkaa-25650/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Kuitenkin yleisinä edellytyksinä odotamme hakijalta kykyä ymmärtää laajoja kokonaisuuksia, kykyä analyyttiseen ajatteluun sekä kykyä selkeään ja laadukkaaseen suomen kielen kirjalliseen sekä suulliseen ilmaisuun, hyvää englannin kielitaitoa, sekä esimerkiksi opintojen myötä tai muutoin hankittua perehtyneisyyttä avointen lähteiden tiedusteluun liittyviin asioihin.”
- Note: phrased as clear, high-quality written and spoken Finnish

**real-14** – [source](https://valtiolle.fi/fi/tyopaikat/kuusi-harjoittelijaa-oikeustradenomi-ita-uudenmaan-karajaoikeudessa-26217/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Viraston pääasiallinen työkieli on suomi, mistä syystä tehtävässä käytännössä edellytetään suomen kielen hyvää taitoa ja ruotsin kielen vähintään tyydyttävää taitoa.”
- Note: word order defeats the old regex

**real-24** – [source](https://kuntarekry.fi/fi/tyopaikat/korkeakouluharjoittelija-liikuntapalvelut-vsa905-02-203-26/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: unclear ✗
- Evidence: “Kielitaitovaatimuksena toisen kotimaisen kielen hyvä suullinen ja kirjallinen taito ja toisen kotimaisen kielen tyydyttävä suullinen ja kirjallinen taito.”
- Note: tricky: good skills in one national language and satisfactory in the other, so Finnish is needed at least at a satisfactory level

**real-30** – [source](https://kuntarekry.fi/fi/tyopaikat/korkeakouluharjoittelija-kl-22-6-26/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: preferred ✗
- Evidence: “sujuvaa kirjallista suomen kielen taitoa; ruotsin kielen osaaminen katsotaan eduksi.”
- Note: 'sujuvaa kirjallista suomen' defeats the old regex

**real-44** – [source](https://kuntarekry.fi/fi/tyopaikat/palomies-kesatyo-ja-muut-sijaisuudet-lansi-uudenmaan-pelastuslaitos-luvn-02-19-26/)
- Label: **preferred** · baseline_v1: not_required · classifier: unclear ✗
- Evidence: “Kaksikielisyys on laajan alueemme rikkaus ja arvostamme molempien kotimaisten kielten osaamista.”
- Note: borderline: 'we value' both national languages

**real-21** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-rikosten-esikasittely-tampere-2-kpl-26177/)
- Label: **unclear** · baseline_v1: not_required · classifier: required ✗
- Evidence: (the ad doesn't mention Finnish)
- Note: no language mentioned in the ad

**real-22** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-rikosten-esikasittely-jyvaskyla-26180/)
- Label: **unclear** · baseline_v1: not_required · classifier: required ✗
- Evidence: (the ad doesn't mention Finnish)
- Note: no language mentioned in the ad

**invented-1** (invented)
- Label: **preferred** · baseline_v1: not_required · classifier: not_needed ✗
- Evidence: “Suomen kielen taito katsotaan eduksi, mutta se ei ole välttämätön.”
- Note: Invented example, written for this project (no real ad).

**invented-3** (invented)
- Label: **preferred** · baseline_v1: required ✗ · classifier: preferred
- Evidence: “Hyvä suomen kielen taito on eduksi.”
- Note: Invented example, written for this project (no real ad).

**invented-6** (invented)
- Label: **not_needed** · baseline_v1: not_required · classifier: unclear ✗
- Evidence: “The working language of the research group is English.”
- Note: Invented example, written for this project (no real ad).

