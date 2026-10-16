# Which coding agent reuses its memory best? Grok vs Codex on the same 11 bugs

*Draft for Tech in General: real numbers from one evening, 14 Oct 2026.*

Every time a coding agent takes a step, it resends the whole conversation: system prompt, tool definitions, files it has read, and its own previous moves. Providers cache the repeated start of that prompt and bill it at a fraction of the price. So the share of input that's a cache hit is one of the biggest levers on what an agent costs.

Published numbers put Claude Code at about 92% and some open-source agents below 50%. I wanted my own numbers for the two CLIs I actually use.

## The test

I used 11 tiny JavaScript bugs from an earlier experiment: duplicate functions, tabs vs spaces, an insert-only fix, a multi-hunk fix, and so on. Each run got a fresh copy of the folder and the same instruction: *make `node test.js` pass without touching `test.js`*. Afterwards my harness ran the test itself and checked that `test.js` was unchanged.

- **Grok Build CLI** (SuperGrok, `grok-4.7-build`): 3 runs per task, 33 in total (the third run one task at a time, to rule out parallel runs warming each other's cache)
- **Codex CLI** (ChatGPT Plus): 1 run per task, 11 in total

## Results

Both agents fixed **every** bug. Neither cheated by editing the test.

| | Grok Build CLI | Codex CLI |
|---|---|---|
| cache hit rate (cached ÷ total input) | **79.7%** | **91.5%** |
| per-task range | 68–88% | 84–95% |
| input tokens per run | ~81K | ~49K |
| wall time per run | 23 s | 36 s |

Codex reused its prompt cache better on every one of the 11 tasks, and it sent about 40% fewer input tokens doing so. Grok was faster.

## Caching is still doing heavy lifting for Grok

Grok's JSON includes an exact cost. At its implied prices ($0.68 per million uncached input tokens, $0.17 per million cached), my 33 runs cost **$0.79**. With zero caching they would have cost **$1.88**. That works out to about 2.4 cents per bug fix instead of 5.7.

## One fixture told me something about personality

One task (`T05_stale`) is a trick: its test *already passes*. Codex noticed and moved on, using about 58K tokens. Grok spent about 10 model calls and about 238K tokens checking whether it was looking at a stale copy of the file. Careful, yes, but four times the tokens.

## Gotcha if you log this yourself

The two CLIs count input differently. Grok's `input_tokens` **excludes** cached tokens (you add `cache_read_input_tokens`). Codex's `input_tokens` **includes** them. Read them the same way and Grok looks like it has a 120% cache hit rate.

## Caveats

- Different models and different system prompts. This compares the products as they ship, not caching technology alone.
- Grok's sequential run scored the same as its parallel runs (80.2%), so warm caches between parallel runs weren't the explanation. Codex ran in parallel only.
- The bugs are tiny. On a real repo, file contents would make up more of the prompt and the numbers would shift.
- Codex's JSON doesn't report a cost, so I can only compare tokens.

*Scripts, raw JSON for every run and the CSVs are in the experiment repo.*
