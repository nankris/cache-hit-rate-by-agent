# #013 Cache hit rate: how much of each agent's input is a cache hit?

**Question.** When a coding agent CLI fixes a small bug, what share of the input tokens it sends are served from the provider's prompt cache (cached ÷ total input)? How do Grok Build CLI and Codex CLI compare on the same tasks?

**Answer, short.** On 11 small JavaScript bug-fix tasks, **Grok Build CLI averaged 79.7%** cache hits (33 runs, per-task range 68–88%). **Codex CLI averaged 91.5%** (11 runs, range 84–95%). Both passed every test, and neither touched `test.js`. Grok also sent more input per task (~81K vs ~49K tokens), so it paid for more uncached tokens on both counts.

## Setup
- Tasks: `/workspace/work/gbarchive/edit-tool-experiment/fixtures/T01..T11`. Each has a `broken.js` and a `test.js` (`node test.js`). For every run the fixture is copied to a fresh temp dir.
- Same prompt for both agents: *"In this directory, `node test.js` currently fails. Fix broken.js so that `node test.js` passes. Do not edit test.js. Run the test to confirm, then reply with one line saying what you changed."*
- Pass check: after the agent exits, the harness runs `node test.js` itself and confirms `test.js` is byte-for-byte unchanged (sha256).
- **Grok:** Grok Build CLI 1.0.52 (SuperGrok), reported model `grok-4.7-build`. Ran `grok --no-auto-update -p "<prompt>" --output-format json --always-approve --disable-web-search`. 3 runs per task (33 total): reps 1–2 ran 4 tasks in parallel (19:29–19:31 IST); rep 3 ran **one at a time, sequentially** (20:15–20:25 IST) to check whether parallelism inflated cache hits. It didn't (80.2%).
- **Codex:** codex-cli 0.162.1 (ChatGPT Plus). The session log shows model `gpt-6.1-sol`. Ran `codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox "<prompt>"` in a throwaway temp git repo. 1 run per task (11 total), 4 in parallel. 2026-10-14, ~19:32–19:36 IST. Codex didn't hit a usage limit.

**Token accounting.** The two CLIs report differently:
- Grok: `input_tokens` **excludes** cache reads, so total input = `input_tokens + cache_read_input_tokens`.
- Codex: `input_tokens` **includes** `cached_input_tokens`, so total input = `input_tokens`.

Hit rate = cached ÷ total input, token-weighted.

```bash
source /workspace/tools/setup.sh
python scripts/run_013_grok.py            # REP=1 (default)
REP=2 python scripts/run_013_grok.py
REP=3 PAR=1 python scripts/run_013_grok.py   # sequential rep (resumable)
python scripts/run_013_codex.py           # resumable; writes results/codex_calls.csv
python scripts/analyse_013.py             # -> results/summary.json, results/summary_by_task.csv, cache_hit_rate.png
```

## Results

| task | Grok total input / run | Grok hit | Grok model calls | Grok ¢/run | Grok pass | Codex total input | Codex hit | Codex pass |
|---|---|---|---|---|---|---|---|---|
| T01_happy | 64,079 | 68.2% | 4.0 | 2.19 | 3/3 | 44,004 | 93.1% | 1/1 |
| T02_duplicate | 64,732 | 79.6% | 4.0 | 1.87 | 3/3 | 44,238 | 92.9% | 1/1 |
| T03_whitespace | 75,889 | 80.3% | 4.7 | 2.20 | 3/3 | 43,495 | 93.6% | 1/1 |
| T04_tabs | 64,092 | 77.8% | 4.0 | 1.89 | 3/3 | 43,327 | 94.0% | 1/1 |
| T05_stale | 238,513 | 87.7% | 10.3 | 6.55 | 3/3 | 58,049 | 94.8% | 1/1 |
| T06_neardup | 64,529 | 74.5% | 4.0 | 2.01 | 3/3 | 43,716 | 84.3% | 1/1 |
| T07_multihunk | 65,005 | 82.4% | 4.0 | 1.82 | 3/3 | 44,362 | 92.6% | 1/1 |
| T08_insert | 64,220 | 72.5% | 4.0 | 2.07 | 3/3 | 58,967 | 86.4% | 1/1 |
| T09_delete | 64,165 | 74.7% | 4.0 | 1.99 | 3/3 | 57,777 | 91.5% | 1/1 |
| T10_replace_all | 64,587 | 77.7% | 4.0 | 1.93 | 3/3 | 44,253 | 92.8% | 1/1 |
| T11_shortctx | 64,435 | 79.8% | 4.0 | 1.84 | 3/3 | 58,834 | 91.4% | 1/1 |

| | Grok Build CLI | Codex CLI |
|---|---|---|
| runs | 33 | 11 |
| tests passed | 33/33 | 11/11 |
| **overall cache hit rate** | **79.7%** (rep 1: 80.7%, rep 2: 78.6%, rep 3 sequential: 80.2%) | **91.5%** |
| median per-task hit rate | 77.8% | 92.9% |
| mean total input per run | 81,295 tokens | 49,184 tokens |
| mean output per run | 856 tokens | 247 tokens |
| mean wall time per run | 22.7 s | 36.1 s |
| API-equivalent cost | 2.40¢/run, $0.79 total | not reported by `codex exec --json` |

**What caching saved Grok:** at the implied prices from #021 ($0.68/M uncached, $0.17/M cached, $2.04/M output), these 33 runs would have cost $1.88 with no caching, against $0.79 actually charged. That's 58% less.

Chart: `cache_hit_rate.png`.

## Caveats
- **T05_stale is a quirk of the fixture:** its `test.js` already passes on the pristine copy. Grok spent ~10 model calls (all three runs) investigating a "stale" snapshot before making a harmless edit. That inflates its token count; leaving T05 out, Grok's mean is ~65K input per run.
- The two agents use different models (`grok-4.7-build` vs `gpt-6.1-sol`) and different system prompts, so this compares *products as shipped*, not caching technology alone.
- Cache hits depend on what ran just before. The sequential rep 3 scored about the same as the parallel reps (80.2% vs 80.7%/78.6%), so parallelism wasn't inflating Grok's number. Codex was only run in parallel.
- "Model calls" for Grok is `num_turns` from its JSON. Codex's JSON reports one `turn.completed` per exec, so its internal call count isn't comparable and isn't shown.
- Small toy tasks: these are tiny files, so the system prompt and tool schema dominate input. On a real repo, file content would be a bigger share.
- Codex's trust prompts added the temp directories as trusted projects in `~/.codex/config.toml`. That's harmless, but it is a side effect.
- The plan also listed Claude Code. It wasn't run here (Grok and Codex only).
