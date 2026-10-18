# model_selection

**Decision:** the corpus was generated with three models, all reached
through OpenRouter with one API key:

- `google/gemini-3.5-flash`
- `deepseek/deepseek-v4-pro`
- `openai/gpt-5.6-sol`

Identifiers read on 19 August 2026. Dissertation Section 4.7, Table A.2
and Appendix C.

## Rejected candidates

| Model | Failure |
|---|---|
| SinLlama | Out of memory on the free T4 across four load configurations |
| Llama-3.1-8B | 11.0 tokens per Sinhala word; degenerate output |
| Kimi K3 | Returned reasoning only, no story content |
| Kimi K2.6 | Reasoning consumed the token budget; 3 of 10 stories |
| gemini-3.7-flash | HTTP 503 on four consecutive attempts |

Because SinLlama could not run on free hardware, the comparison covers
commercial models only. This is stated as a limitation in the dissertation.

## Generation settings

Prompt variant A2 (English instruction block, Sinhala topic description,
register not instructed), temperature 0.7, length gate 720–880 words, up to
four attempts per topic. Attempts needed for ten accepted stories: Gemini
14, DeepSeek 26, GPT 13. The generation code is in `pipeline/01_generate.py`;
the story-generation outputs are in the separate repository
https://github.com/VihangaDeshan/SSEF.
