import json
from datetime import datetime, timezone
from pathlib import Path


SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
LATEST_FILE = SNAPSHOT_DIR / "allsvenskan_latest.json"
FIXTURES_FILE = SNAPSHOT_DIR / "fixtures_latest.json"


def save_bootstrap(data):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }

    latest_json = json.dumps(payload, ensure_ascii=False, indent=2)
    LATEST_FILE.write_text(latest_json, encoding="utf-8")

    dated_file = SNAPSHOT_DIR / f"allsvenskan_{datetime.now(timezone.utc).date().isoformat()}.json"
    if not dated_file.exists():
        dated_file.write_text(latest_json, encoding="utf-8")


def load_latest_bootstrap():
    if not LATEST_FILE.exists():
        return None
    return _read_snapshot(LATEST_FILE)


def load_previous_bootstrap():
    snapshots = sorted(SNAPSHOT_DIR.glob("allsvenskan_*.json"), reverse=True)
    today_name = f"allsvenskan_{datetime.now(timezone.utc).date().isoformat()}.json"

    for path in snapshots:
        if path.name == "allsvenskan_latest.json" or path.name == today_name:
            continue
        return _read_snapshot(path)

    return None


def save_fixtures(data):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    FIXTURES_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_latest_fixtures():
    if not FIXTURES_FILE.exists():
        return None
    return _read_snapshot(FIXTURES_FILE)


def _read_snapshot(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "fetched_at": payload.get("fetched_at"),
            "data": payload["data"],
        }
    except (OSError, json.JSONDecodeError, KeyError):
        return None
