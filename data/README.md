# data/

## What is in this repository

| Path | Contents | Public |
|---|---|---|
| `stories/generated30_stories.json` | The 30 LLM-generated stories | yes |
| `stories/private/human8_stories.json` | The 8 published human reference stories | **no — gitignored** |
| `stories/human8_sources.csv` | Bibliographic record of the 8 human stories | yes |
| `scores/all38_v4_scores.csv` | Per-dimension scores, all 38 texts, segmenter v4 | yes |
| `scores/composite_scores.csv` | z-scores and composite, all 38 texts | yes |

## Why the human texts are not published

The eight reference texts are published Sinhala short stories by named
authors. Their copyright is held by the authors or their publishers, not by
this project. Redistributing them inside an MIT-licensed repository would
be republication under a licence this project has no standing to grant.

The **scores** are a different matter and do ship. A perplexity value or a
DARC score is a measurement made about a text, not a reproduction of it,
and the 38-row score tables are what the reported figures are computed
from. Anyone can therefore reproduce every number in the dissertation from
this repository, including the human reference distribution that the
composite is normalised against, without the texts themselves.

Reproducing the scores **from source** requires obtaining the eight stories
independently. `stories/human8_sources.csv` records where each came from so
that this is possible.

## Keying — read before joining these files

`id` is **not unique**. It identifies the topic setting, not the story.
The generation design is crossed: each of the ten topics was attempted by
all three models, so `N01_CoastTrain` names three different stories.

    38 rows · 18 distinct `id` values · 38 distinct `(id, model)` pairs

Any join keyed on `id` alone silently collapses the corpus to 18 rows and
keeps whichever row happened to be read last. **Key on `(id, model)`.**

## Segmenter version

All score files here are segmenter **v4** (dialogue spans may not cross a
paragraph break). Any file named `all38_full_scores.csv` is the earlier v3
output and must not be used: it reports H07 DARC as 0.1833 where v4 gives
0.9718, and H02 as 0.5133 where v4 gives 0.5632.

`pppl_narrative` and `pppl_dialogue` are empty in `all38_v4_scores.csv`.
Only `pppl_overall` is populated, because only it is independent of
segmentation. The per-register values are produced by pipeline stage 03 and
have not yet been written back to this file.
