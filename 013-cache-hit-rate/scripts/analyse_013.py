import pandas as pd, numpy as np, json, os, glob, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
g = pd.read_csv(f"{D}/results/grok_calls.csv")
g["total_in"] = g.input_tokens + g.cache_read_input_tokens          # Grok: input_tokens excludes cache reads
runs = {(j["task"], j["rep"]): j for j in (json.load(open(f)) for f in glob.glob(f"{D}/results/runs/grok_*.json"))}
g["test_pass"] = [runs[(t, r)]["test_pass"] for t, r in zip(g.label, g.rep)]
g["test_js_untouched"] = [runs[(t, r)]["test_js_untouched"] for t, r in zip(g.label, g.rep)]
c = pd.read_csv(f"{D}/results/codex_calls.csv")
c["total_in"] = c.input_tokens                                      # Codex: input_tokens includes cached
gt = g.groupby("label").agg(total_in=("total_in", "sum"), cached=("cache_read_input_tokens", "sum"), cost=("cost_usd", "mean"),
                            model_calls=("num_turns", "mean"), passes=("test_pass", "sum"), runs=("rep", "size"))
gt["grok_hit"] = gt.cached / gt.total_in
c = c.set_index("task"); c["codex_hit"] = c.cached_input_tokens / c.total_in
t = gt.join(c[["total_in", "cached_input_tokens", "codex_hit", "test_pass"]], rsuffix="_codex")
t.round(4).to_csv(f"{D}/results/summary_by_task.csv")
# Grok first rep vs second rep
byrep = g.groupby("rep").apply(lambda x: x.cache_read_input_tokens.sum() / x.total_in.sum())
# token-weighted cost had there been zero caching (implied price 0.68 / 0.17 per M from #021)
nocache = ((g.total_in * 0.68 + g.output_tokens * 2.04) / 1e6).sum()
s = dict(grok_runs=len(g), grok_pass=int(g.test_pass.sum()), grok_test_js_untouched=int(g.test_js_untouched.sum()),
         grok_overall_hit=round(g.cache_read_input_tokens.sum() / g.total_in.sum(), 4),
         grok_hit_by_rep={int(k): round(v, 4) for k, v in byrep.items()},
         grok_median_task_hit=round(float(gt.grok_hit.median()), 4), grok_min_task_hit=round(float(gt.grok_hit.min()), 4), grok_max_task_hit=round(float(gt.grok_hit.max()), 4),
         grok_mean_input_per_run=round(g.total_in.mean()), grok_mean_cost_usd=round(g.cost_usd.mean(), 5), grok_total_cost_usd=round(g.cost_usd.sum(), 4),
         grok_cost_if_no_cache_usd=round(nocache, 4), grok_mean_model_calls=round(g.num_turns.mean(), 2),
         codex_runs=len(c), codex_pass=int(c.test_pass.sum()), codex_overall_hit=round(c.cached_input_tokens.sum() / c.total_in.sum(), 4),
         codex_median_task_hit=round(float(c.codex_hit.median()), 4), codex_mean_input_per_run=round(c.total_in.mean()),
         models=sorted(set(g.model)), first=g.ts_ist.min(), last=g.ts_ist.max())
json.dump(s, open(f"{D}/results/summary.json", "w"), indent=1); print(json.dumps(s, indent=1)); print(t.round(3).to_string())
fig, ax = plt.subplots(figsize=(10, 5)); x = np.arange(len(t))
ax.bar(x - 0.2, t.grok_hit * 100, 0.4, label=f"Grok Build CLI ({len(g)} runs, {g.rep.nunique()} per task) overall {s['grok_overall_hit']*100:.0f}%", color="#4C72B0")
ax.bar(x + 0.2, t.codex_hit * 100, 0.4, label=f"Codex CLI exec ({len(c)} runs) overall {s['codex_overall_hit']*100:.0f}%", color="#55A868")
ax.set_xticks(x); ax.set_xticklabels([i.split("_", 1)[1] for i in t.index], rotation=30); ax.set_ylim(0, 100)
ax.set_ylabel("cached ÷ total input tokens (%)"); ax.set_title("Prompt-cache hit rate on 11 small JS bug-fix tasks (all tests passed)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2); ax.grid(axis="y", alpha=.3); plt.tight_layout(); plt.savefig(f"{D}/cache_hit_rate.png", dpi=130)
