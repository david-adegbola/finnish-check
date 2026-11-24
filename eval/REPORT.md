# Evaluation report

Date: 2026-11-24 · Classifier mode: **live** (claude-haiku-5-5)
 · Ads: 38 (30 real excerpts, 8 invented)

## Collapsed: required vs not required

Preferred and not_needed count as not_required; 10 ads labelled unclear are left out.

### baseline_v1 (JobDesk's keyword rule), all ads

Accuracy: **57%** (16 of 28)

| true label \ predicted | required | not_required |
|---|---|---|
| required | 9 | 11 |
| not_required | 1 | 7 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 90% | 45% | 20 |
| not_required | 39% | 88% | 8 |

### baseline_v1, real ads only

Accuracy: **45%** (9 of 20)

| true label \ predicted | required | not_required |
|---|---|---|
| required | 8 | 11 |
| not_required | 0 | 1 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 100% | 42% | 19 |
| not_required | 8% | 100% | 1 |

### Classifier (live), real ads only

Accuracy: **95%** (19 of 20)

| true label \ predicted | required | not_required | unclear |
|---|---|---|---|
| required | 18 | 0 | 1 |
| not_required | 0 | 1 | 0 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 100% | 95% | 19 |
| not_required | 100% | 100% | 1 |

### Classifier (live), all ads

Accuracy: **96%** (27 of 28)

| true label \ predicted | required | not_required | unclear |
|---|---|---|---|
| required | 19 | 0 | 1 |
| not_required | 0 | 8 | 0 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 100% | 95% | 20 |
| not_required | 100% | 100% | 8 |

## Four levels (classifier only)

### Classifier (live)

Accuracy: **92%** (35 of 38)

| true label \ predicted | required | preferred | not_needed | unclear |
|---|---|---|---|---|
| required | 19 | 0 | 0 | 1 |
| preferred | 0 | 5 | 0 | 0 |
| not_needed | 0 | 0 | 3 | 0 |
| unclear | 0 | 2 | 0 | 8 |

| class | precision | recall | ads |
|---|---|---|---|
| required | 100% | 95% | 20 |
| preferred | 71% | 100% | 5 |
| not_needed | 100% | 100% | 3 |
| unclear | 89% | 80% | 10 |

## Labels corrected after an LLM run

Changing a label after seeing the model's answer can flatter the results, so every such change is listed here with its reason.

- **real-46** → required: Corrected after the first LLM run (was 'unclear', citing the English-skills sentence): the ad states a national-languages requirement, the same rule as real-24.

## Disagreements

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
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Suomen kielen taitosi on erinomainen, englannin ja ruotsin taidot sekä hyvä kirjallinen ilmaisu ovat eduksi.”
- Note: word order defeats the old regex

**real-7** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-lupapalveluyksikko-26564/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Korkeakouluharjoittelijalta edellytämme hyvää suomen ja käytännön ruotsin ja englannin kielen taitoa.”
- Note: 'suomen ja ... kielen' defeats the old regex

**real-10** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-26540/)
- Label: **unclear** · baseline_v1: not_required · classifier: preferred ✗
- Evidence: “Länsi-Uudenmaan poliisilaitos on kaksikielinen, joten hakijalle voidaan katsoa eduksi, että hän kykenee tulkitsemaan ruotsinkielisiä asiakirjoja.”
- Note: only Swedish mentioned

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

**real-17** – [source](https://valtiolle.fi/fi/tyopaikat/korkeakouluharjoittelija-26344/)
- Label: **unclear** · baseline_v1: not_required · classifier: preferred ✗
- Evidence: “Länsi-Uudenmaan poliisilaitos on kaksikielinen, joten hakijalle voidaan katsoa eduksi, että hän kykenee tekemään päätösluonnoksia ja rajoitusesityksiä myös ruotsin kielellä.”
- Note: only Swedish mentioned

**real-24** – [source](https://kuntarekry.fi/fi/tyopaikat/korkeakouluharjoittelija-liikuntapalvelut-vsa905-02-203-26/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: unclear ✗
- Evidence: “Kielitaitovaatimuksena toisen kotimaisen kielen hyvä suullinen ja kirjallinen taito ja toisen kotimaisen kielen tyydyttävä suullinen ja kirjallinen taito.”
- Note: tricky: good skills in one national language and satisfactory in the other, so Finnish is needed at least at a satisfactory level

**real-30** – [source](https://kuntarekry.fi/fi/tyopaikat/korkeakouluharjoittelija-kl-22-6-26/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “sujuvaa kirjallista suomen kielen taitoa; ruotsin kielen osaaminen katsotaan eduksi.”
- Note: 'sujuvaa kirjallista suomen' defeats the old regex

**real-46** – [source](https://kuntarekry.fi/fi/tyopaikat/hogskolepraktikant-idrottsservice-vsa905-02-203-26/)
- Label: **required** · baseline_v1: not_required ✗ · classifier: required
- Evidence: “Språkkunskapskravet är god förmåga att i tal och skrift använda det ena inhemska språket och nöjaktig förmåga att i tal och skrift använda det andra inhemska språket.”
- Note: Corrected after the first LLM run (was 'unclear', citing the English-skills sentence): the ad states a national-languages requirement, the same rule as real-24.

**invented-3** (invented)
- Label: **preferred** · baseline_v1: required ✗ · classifier: preferred
- Evidence: “Hyvä suomen kielen taito on eduksi.”
- Note: Invented example, written for this project (no real ad).

