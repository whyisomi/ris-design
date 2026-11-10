#!/usr/bin/env python3
"""Загрузка фото проектов РИС-Дизайн с публичного Яндекс Диска.
Источник: https://disk.yandex.ru/d/3U4zBqb5OD65BQ (папка "Дизайн-проект (2)")
Public API без OAuth-токена. 429 отдаётся мгновенно — ретраим без пауз, 24 потока.
"""
import json, os, pathlib, random, sys, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://cloud-api.yandex.net/v1/disk/public/resources"
SHARE = "https://disk.yandex.ru/d/3U4zBqb5OD65BQ"
LONG = open("/tmp/opencode/long_key.txt").read().strip()
RAW_ROOT = pathlib.Path(os.environ.get("RIS_ORIGINALS", "/home/iso/rissite-originals"))
MANIFEST = RAW_ROOT / "manifest.json"
WORKERS = 24
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
stats = {"ok": 0, "429": 0, "err": 0}
slock = threading.Lock()

def get_href(path):
    """Мгновенный ретрай: 429 приходит без задержки, ждать бессмысленно."""
    q = urllib.parse.urlencode({"public_key": LONG, "path": path})
    url = f"{BASE}/download?{q}"
    for a in range(400):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            with slock: stats["ok"] += 1
            return d["href"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                with slock: stats["429"] += 1
                continue
            raise RuntimeError(f"HTTP {e.code}")
        except Exception:
            with slock: stats["err"] += 1
            time.sleep(0.3)
            continue
    raise RuntimeError("лимит попыток исчерпан")

def fetch(entry):
    dest = RAW_ROOT / entry["path"].lstrip("/")
    if dest.exists() and dest.stat().st_size == entry["size"]:
        return "skip", entry, None
    for a in range(10):
        try:
            href = get_href(entry["path"])
            req = urllib.request.Request(href, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r: data = r.read()
            if len(data) != entry["size"]: raise RuntimeError("размер не совпал")
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part"); tmp.write_bytes(data); tmp.rename(dest)
            return "ok", entry, None
        except Exception as exc:
            err = str(exc); time.sleep(0.5 + random.random())
            continue
    return "fail", entry, "попытки исчерпаны"

def main():
    entries = json.load(open("/tmp/opencode/plan_files.json"))
    total = sum(e["size"] for e in entries)
    print(f"{SHARE}\nФайлов: {len(entries)}  объём: {total/1024/1024:.1f} MB", flush=True)
    started = time.time(); res = []; n = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for fut in [pool.submit(fetch, e) for e in entries]:
            status, entry, err = fut.result(); res.append((status, entry, err)); n += 1
            if status == "fail": print(f"  !! {entry['path']}: {err}", flush=True)
            if n % 5 == 0 or status == "fail":
                el = time.time()-started; rate = n/el*60
                print(f"  {n}/{len(entries)}  {rate:.1f} фото/мин  (429: {stats['429']})  ETA {(len(entries)-n)/max(rate,.01):.0f} мин", flush=True)
    ok = sum(1 for s,_,_ in res if s=="ok"); sk = sum(1 for s,_,_ in res if s=="skip"); fail = sum(1 for s,_,_ in res if s=="fail")
    print(f"\nСкачано {ok}, уже было {sk}, ошибок {fail}", flush=True)
    projects, index = [], {}
    for s, e, _ in res:
        if e["project"] not in index:
            index[e["project"]] = {"name": e["project"], "rooms": [], "files": []}; projects.append(index[e["project"]])
        p = index[e["project"]]; item = {"name": e["name"], "path": e["path"], "size": e["size"]}
        p["files"].append(item)
        if e["room"] not in {r["name"] for r in p["rooms"]}: p["rooms"].append({"name": e["room"], "files": []})
        next(r for r in p["rooms"] if r["name"] == e["room"])["files"].append(item)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({"source": SHARE, "total_files": len(entries), "total_bytes": total,
        "projects": projects, "errors": [{"path": e["path"], "error": err} for s,e,err in res if s=="fail"]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Манифест: {MANIFEST}", flush=True)
    sys.exit(1 if fail else 0)

if __name__ == "__main__": main()
