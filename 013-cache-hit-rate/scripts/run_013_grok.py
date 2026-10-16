# Run the 11 edit-tool fixtures through Grok Build CLI headless; log usage, verify tests.
import os, sys, shutil, tempfile, hashlib, subprocess, json, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__))
from grok_log import run_grok, QuotaHit
FIX = "/workspace/work/gbarchive/edit-tool-experiment/fixtures"
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(D, "results", "grok_calls.csv")
REP = int(os.environ.get("REP", 1))
PROMPT = ("In this directory, `node test.js` currently fails. Fix broken.js so that `node test.js` passes. "
          "Do not edit test.js. Run the test to confirm, then reply with one line saying what you changed.")
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def job(t):
    wd = tempfile.mkdtemp(prefix=f"g013_{t}_"); shutil.copytree(os.path.join(FIX, t), wd, dirs_exist_ok=True)
    h0 = sha(os.path.join(wd, "test.js"))
    r = run_grok(PROMPT, t, CSV, "013-grok", REP, cwd=wd, extra=["--always-approve", "--disable-web-search"])
    p = subprocess.run(["node", "test.js"], cwd=wd, capture_output=True, text=True)
    res = dict(task=t, rep=REP, test_pass=p.returncode == 0, test_js_untouched=sha(os.path.join(wd, "test.js")) == h0,
               text=r["text"], usage=r["raw"].get("usage"), cost=r["cost_usd"], turns=r["num_turns"], latency=r["latency_s"])
    json.dump(res | {"raw": r["raw"]}, open(os.path.join(D, "results", "runs", f"grok_{t}_r{REP}.json"), "w"), indent=1)
    return t, res["test_pass"], res["test_js_untouched"], r["cost_usd"], r["cache_read_input_tokens"], r["input_tokens"]
tasks = [t for t in sorted(os.listdir(FIX)) if not os.path.exists(os.path.join(D, "results", "runs", f"grok_{t}_r{REP}.json"))]  # resumable
with cf.ThreadPoolExecutor(int(os.environ.get("PAR", 4))) as ex:
    for f in cf.as_completed([ex.submit(job, t) for t in tasks]):
        try: print(f.result(), flush=True)
        except QuotaHit as e: print("QUOTA HIT", e); sys.exit(3)
