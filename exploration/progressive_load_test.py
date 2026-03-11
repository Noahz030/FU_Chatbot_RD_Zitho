import json
import argparse
import statistics
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import error, request

URL = "https://chatbot-arena.ki-campus.org/arena/generate"
HEADERS = {"Content-Type": "application/json"}
QUESTION = "Ich möchte Prompting lernen"
TIMEOUT = 95
RESULTS_DIR = Path(__file__).parent / "loadtest_results"


def one_call(session_id: str):
    payload = json.dumps({"session_id": session_id, "question": QUESTION}).encode("utf-8")
    req = request.Request(URL, data=payload, headers=HEADERS, method="POST")
    start = time.time()
    body = ""
    code = 0

    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", errors="ignore")
    except error.HTTPError as exc:
        code = exc.code
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
    except Exception:
        code = 0

    duration = time.time() - start
    demo = ("Demo-Modus" in body) or ("Beispielantwort" in body)
    return code, duration, demo


def summarize(name: str, results):
    codes = {}
    lats = [r[1] for r in results]
    demo_count = sum(1 for r in results if r[2])

    for code, _, _ in results:
        codes[code] = codes.get(code, 0) + 1

    print(f"=== {name} ===")
    for code in sorted(codes):
        print(f"code {code}: {codes[code]}")
    print(
        "lat avg={:.2f}s min={:.2f}s max={:.2f}s".format(
            statistics.mean(lats), min(lats), max(lats)
        )
    )
    print(f"demo_fallback_files:{demo_count}")
    print()

    return {
        "scenario": name,
        "count": len(results),
        "codes": codes,
        "latency_avg_s": statistics.mean(lats),
        "latency_min_s": min(lats),
        "latency_max_s": max(lats),
        "demo_fallback_files": demo_count,
    }


def run_serial(n: int, name: str):
    results = []
    for i in range(1, n + 1):
        sid = f"{name}-{i}-{int(time.time())}-{i}"
        results.append(one_call(sid))
    return summarize(name, results)


def run_parallel(n: int, name: str):
    results = []
    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = [
            executor.submit(one_call, f"{name}-{i}-{int(time.time())}-{i}")
            for i in range(1, n + 1)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return summarize(name, results)


def run_ramp(n: int, delay_seconds: int, name: str):
    results = [None] * n
    lock = threading.Lock()

    def worker(index: int):
        if index > 0:
            time.sleep(index * delay_seconds)
        sid = f"{name}-{index + 1}-{int(time.time())}-{index + 1}"
        res = one_call(sid)
        with lock:
            results[index] = res

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return summarize(name, results)


def save_results(run: dict) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = run["run_id"]

    json_path = RESULTS_DIR / f"{run_id}.json"
    json_path.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = RESULTS_DIR / "summary.csv"
    write_header = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8") as fh:
        if write_header:
            fh.write(
                "run_id,timestamp,label,scenario,count,code_200,code_429,code_502,code_503,code_504,code_000,"
                "lat_avg_s,lat_min_s,lat_max_s,demo_fallback_files,config\n"
            )

        for s in run["scenarios"]:
            codes = s["codes"]
            fh.write(
                f"{run_id},{run['timestamp']},{run['label']},{s['scenario']},{s['count']},"
                f"{codes.get(200, 0)},{codes.get(429, 0)},{codes.get(502, 0)},{codes.get(503, 0)},{codes.get(504, 0)},{codes.get(0, 0)},"
                f"{s['latency_avg_s']:.3f},{s['latency_min_s']:.3f},{s['latency_max_s']:.3f},{s['demo_fallback_files']},"
                f"\"{run['config']}\"\n"
            )

    return json_path, csv_path


def parse_args():
    parser = argparse.ArgumentParser(description="Progressive load test for /arena/generate")
    parser.add_argument(
        "--label",
        default="manual",
        help="Short label for this run, e.g. c4_a45_p42",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Free-text config snapshot stored with results",
    )
    parser.add_argument(
        "--profile",
        choices=["api-stress", "human-like-prefetch", "both"],
        default="both",
        help="Which test profile to run",
    )
    parser.add_argument("--human-users", type=int, default=5, help="Users for human-like profile")
    parser.add_argument("--human-rounds", type=int, default=4, help="Rounds per user in human-like profile")
    parser.add_argument("--human-stagger", type=int, default=2, help="Start stagger in seconds between users")
    parser.add_argument("--human-think", type=int, default=3, help="Think time in seconds before using prefetched result")
    return parser.parse_args()


def run_human_like_prefetch(users: int, rounds: int, stagger_seconds: int, think_seconds: int, name: str):
    """Simulate users with one in-flight background prefetch after first visible request."""
    results = []
    lock = threading.Lock()

    def user_flow(user_idx: int):
        if user_idx > 0:
            time.sleep(user_idx * stagger_seconds)

        # First request is visible to user.
        first_sid = f"{name}-u{user_idx + 1}-r1-{int(time.time())}"
        first_result = one_call(first_sid)
        with lock:
            results.append(first_result)

        prefetched_result = None

        # Remaining rounds: background prefetch while user is reading/thinking.
        for round_idx in range(2, rounds + 1):
            sid = f"{name}-u{user_idx + 1}-r{round_idx}-{int(time.time())}"

            holder = {"result": None}

            def do_prefetch():
                holder["result"] = one_call(sid)

            t = threading.Thread(target=do_prefetch, daemon=True)
            t.start()

            time.sleep(think_seconds)
            t.join()
            prefetched_result = holder["result"]

            with lock:
                results.append(prefetched_result)

    threads = [threading.Thread(target=user_flow, args=(i,), daemon=True) for i in range(users)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return summarize(name, results)


if __name__ == "__main__":
    args = parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    timestamp = datetime.now(timezone.utc).isoformat()

    scenarios = []
    if args.profile in ("api-stress", "both"):
        scenarios.extend(
            [
                run_serial(5, "S1_serial_5"),
                run_parallel(3, "S2_parallel_3"),
                run_parallel(6, "S3_parallel_6"),
                run_parallel(8, "S4_parallel_8"),
                run_parallel(10, "S5_parallel_10"),
                run_ramp(15, 2, "S6_ramp15_d2"),
                run_parallel(15, "S7_burst15"),
            ]
        )

    if args.profile in ("human-like-prefetch", "both"):
        scenarios.extend(
            [
                run_human_like_prefetch(
                    users=args.human_users,
                    rounds=args.human_rounds,
                    stagger_seconds=args.human_stagger,
                    think_seconds=args.human_think,
                    name=f"H1_human_prefetch_u{args.human_users}_r{args.human_rounds}_s{args.human_stagger}_t{args.human_think}",
                ),
            ]
        )

    run = {
        "run_id": run_id,
        "timestamp": timestamp,
        "label": args.label,
        "config": args.config,
        "url": URL,
        "question": QUESTION,
        "timeout": TIMEOUT,
        "scenarios": scenarios,
    }

    json_path, csv_path = save_results(run)
    print(f"Saved JSON: {json_path}")
    print(f"Updated CSV: {csv_path}")
