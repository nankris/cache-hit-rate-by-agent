# Same 11 fixtures, once, through `codex exec --json`. Codex input_tokens INCLUDES cached_input_tokens.
import os, sys, shutil, tempfile, hashlib, subprocess, json, csv, time, concurrent.futures as cf, re
FIX = "/workspace/work/gbarchive/edit-tool-experiment/fixtures"
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(D, "results", "codex_calls.csv")
PROMPT = ("In this directory, `node test.js` currently fails. Fix broken.js so that `node test.js` passes. "
          "Do not edit test.js. Run the test to confirm, then reply with one line saying what you changed.")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
F = ["task", "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "turns", "latency_s", "test_pass", "test_js_untouched", "error"]
def job(t):
    wd = tempfile.mkdtemp(prefix=f"c013_{t}_"); shutil.copytree(os.path.join(FIX, t), wd, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-q", "."], cwd=wd)
    h0 = sha(os.path.join(wd, "test.js")); t0 = time.time()
    p = subprocess.run(["codex", "exec", "--json", "--skip-git-repo-check", "--dangerously-bypass-approvals-and-sandbox", PROMPT],
                       cwd=wd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
    lat = time.time() - t0
    ev = []
    for line in p.stdout.splitlines():
        try: ev.append(json.loads(line))
        except Exception: pass
    agg = dict(input_tokens=0, cached_input_tokens=0, output_tokens=0, reasoning_output_tokens=0); turns = 0; err = ""
    for e in ev:
        if e.get("type") == "turn.completed":
            turns += 1
            for k in agg: agg[k] += e["usage"].get(k, 0)
        if e.get("type") in ("error", "turn.failed"): err += json.dumps(e)[:300]
    tp = subprocess.run(["node", "test.js"], cwd=wd, capture_output=True).returncode == 0
    row = dict(task=t, **agg, turns=turns, latency_s=round(lat, 1), test_pass=tp,
               test_js_untouched=sha(os.path.join(wd, "test.js")) == h0, error=err)
    json.dump({"row": row, "events": ev, "stderr": p.stderr[-2000:]}, open(os.path.join(D, "results", "runs", f"codex_{t}.json"), "w"), indent=1)
    return row
done = {f[6:-5] for f in os.listdir(os.path.join(D, "results", "runs")) if f.startswith("codex_")}
TASKS = [t for t in sorted(os.listdir(FIX)) if t not in done]  # resumable
with cf.ThreadPoolExecutor(4) as ex:
    for f in cf.as_completed([ex.submit(job, t) for t in TASKS]):
        print(f.result(), flush=True)
with open(CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=F); w.writeheader(); w.writerows([json.load(open(os.path.join(D, "results", "runs", f"codex_{t}.json")))["row"] for t in sorted(os.listdir(FIX))])
