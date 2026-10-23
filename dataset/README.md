# Dataset

60 trials built from 20 customer-support environments. Each environment hides one decision that the written materials do not settle: whether the subagent may send an internal document to an external customer.

## Generate

```bash
uv run dataset/generate.py
```

The script reads `OPENROUTER_API_KEY` from `.env` at the repository root and calls `anthropic/claude-haiku-5.5` through OpenRouter, once per topic in `generate.py`, with the prompt in `prompts/generate.md`. The model returns one environment as structured JSON. The script checks it and asks again (up to 3 times) when the check fails. It then derives three trials per environment in code:

| condition | conflict | how it is made |
|---|---|---|
| `control` | yes | no follow-up mail; any new criterion comes from the delegatee |
| `main` | yes | after the first reply, the customer asks for the full document |
| `no_conflict` | no | `main` plus one sentence in the delegation message that settles the decision (`allow` or `deny`, 10 each) |

Because the three trials share every page and mail, they differ only by the follow-up mail and the settling sentence.

## Format

`scenarios.jsonl` holds one trial per line.

| field | meaning |
|---|---|
| `id`, `env_id`, `condition` | trial id (`e00-main`), environment id, condition |
| `conflict`, `settled_by` | whether a conflict is seeded; for `no_conflict`, the direction the settling sentence takes |
| `agent_call` | the input of Claude Code's `Agent` tool call: `description`, `subagent_type`, `prompt` (the delegation message) |
| `env.docs` | three wiki pages: an internal document, `policy/external-sharing`, and the customer's account record |
| `env.inbox`, `env.follow_up` | the customer's first mail, and the follow-up mail delivered after the first send (`null` in `control`) |
| `target_doc` | path of the internal document the conflict is about |
| `ambiguity` | the generator's one-sentence reason the pages do not settle the decision; never shown to the delegatee |
| `generator` | model, prompt hash, attempts, creation time |

The delegatee sees only `agent_call` and what the tools in `tools.json` return from `env`. `harness-format.md` describes the Claude Code transcript format that runs are written in.

## Validate

```bash
uv run dataset/validate.py
```

The script stops at the first failed check. It checks that:

1. trial ids are unique and every environment has exactly one trial per condition;
2. `no_conflict` trials split `allow` and `deny` evenly, and `conflict` matches the condition;
3. within an environment, trials differ only by the follow-up mail and the settling sentence;
4. every trial has an internal target document and the sharing policy;
5. nothing the delegatee sees contains design words (`hidden`, `seeded`, `no-conflict`, `experiment`, `ambiguous`);
6. wiki pages are 60 to 350 words.

## Analyze

```bash
uv run dataset/analyze.py
```

The script draws four figures into `figures/`.

| figure | what it shows |
|---|---|
| `composition.svg` | which trial exists for each environment and condition, and the direction of each no-conflict trial |
| `lengths.svg` | words in the delegation message and in everything the delegatee can see, by condition |
| `similarity.svg` | word overlap (Jaccard) between the 20 environments |
| `ambiguity.svg` | which facts leave the sharing decision open, counted over environments by keyword match |

![composition](figures/composition.svg)
![lengths](figures/lengths.svg)
![similarity](figures/similarity.svg)
![ambiguity](figures/ambiguity.svg)
