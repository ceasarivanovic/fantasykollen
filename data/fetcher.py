import re
import time
import unicodedata
from datetime import datetime, timezone

import requests

from data.cache import (
    load_latest_bootstrap,
    load_latest_fixtures,
    load_previous_bootstrap,
    save_bootstrap,
    save_fixtures,
)


BASE_URL = "https://fantasy.allsvenskan.se/api/"
POSITIONS = {1: "MV", 2: "Back", 3: "Mittfält", 4: "Anfall"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
CACHE_TTL_SECONDS = 15 * 60
_bootstrap_payload_cache = {"time": 0, "payload": None}
_fixtures_payload_cache = {"time": 0, "payload": None}


def get_bootstrap_payload():
    now = time.time()
    if (
        _bootstrap_payload_cache["payload"] is not None
        and now - _bootstrap_payload_cache["time"] < CACHE_TTL_SECONDS
    ):
        return _bootstrap_payload_cache["payload"]

    try:
        response = requests.get(f"{BASE_URL}bootstrap-static/", headers=HEADERS, timeout=12)
        response.raise_for_status()
        data = response.json()
        save_bootstrap(data)
        payload = {
            "data": data,
            "meta": {
                "source": "live",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "using_cache": False,
            },
        }
        _bootstrap_payload_cache.update({"time": now, "payload": payload})
        return payload
    except requests.RequestException:
        cached = load_latest_bootstrap()
        if cached:
            payload = {
                "data": cached["data"],
                "meta": {
                    "source": "cache",
                    "fetched_at": cached["fetched_at"],
                    "using_cache": True,
                },
            }
            _bootstrap_payload_cache.update({"time": now, "payload": payload})
            return payload
        raise


def get_allsvenskan_data():
    payload = get_bootstrap_payload()
    data = payload["data"]
    fixtures_payload = get_fixtures_payload()
    previous = load_previous_bootstrap()
    active_team_ids = get_fixture_team_ids(fixtures_payload["data"])
    teams = build_teams(data, active_team_ids)

    return {
        "event": get_current_event(data),
        "events": build_events(data),
        "teams": teams,
        "players": build_players(data, teams, previous["data"] if previous else None),
        "fixtures": build_fixtures(fixtures_payload["data"], teams),
        "meta": {
            **payload["meta"],
            "previous_snapshot_at": previous["fetched_at"] if previous else None,
            "fixtures_source": fixtures_payload["meta"]["source"],
            "fixtures_fetched_at": fixtures_payload["meta"].get("fetched_at"),
        },
    }


def refresh_allsvenskan_data():
    _bootstrap_payload_cache.update({"time": 0, "payload": None})
    _fixtures_payload_cache.update({"time": 0, "payload": None})
    return get_allsvenskan_data()


def get_fixtures_payload():
    now = time.time()
    if (
        _fixtures_payload_cache["payload"] is not None
        and now - _fixtures_payload_cache["time"] < CACHE_TTL_SECONDS
    ):
        return _fixtures_payload_cache["payload"]

    try:
        response = requests.get(f"{BASE_URL}fixtures/", headers=HEADERS, timeout=12)
        response.raise_for_status()
        data = response.json()
        save_fixtures(data)
        payload = {
            "data": data,
            "meta": {
                "source": "live",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        _fixtures_payload_cache.update({"time": now, "payload": payload})
        return payload
    except requests.RequestException:
        cached = load_latest_fixtures()
        if cached:
            payload = {
                "data": cached["data"],
                "meta": {
                    "source": "cache",
                    "fetched_at": cached["fetched_at"],
                },
            }
            _fixtures_payload_cache.update({"time": now, "payload": payload})
            return payload
        payload = {
            "data": [],
            "meta": {"source": "missing", "fetched_at": None},
        }
        _fixtures_payload_cache.update({"time": now, "payload": payload})
        return payload


def build_teams(data, active_team_ids=None):
    return [
        {
            "id": team["id"],
            "name": team["name"],
            "slug": slugify(team["name"]),
            "short_name": team["short_name"],
            "code": team.get("code"),
        }
        for team in data["teams"]
        if active_team_ids is None or team["id"] in active_team_ids
    ]


def build_players(data, teams, previous_data=None):
    team_lookup = {team["id"]: team["name"] for team in teams}
    previous_players = build_previous_player_lookup(previous_data)
    players = []

    for player in data["elements"]:
        if player["team"] not in team_lookup:
            continue

        previous = previous_players.get(player["id"], {})
        name = f"{player['first_name']} {player['second_name']}".strip()
        price = player["now_cost"] / 10
        form = as_float(player.get("form"))
        selected_by_percent = as_float(player.get("selected_by_percent"))

        players.append(
            {
                "id": player["id"],
                "name": name,
                "slug": f"{slugify(name)}-{player['id']}",
                "team": team_lookup[player["team"]],
                "team_slug": slugify(team_lookup[player["team"]]),
                "price": price,
                "price_change": rounded_delta(price, previous.get("price")),
                "total_points": player["total_points"],
                "points_per_game": as_float(player.get("points_per_game")),
                "minutes": player.get("minutes", 0),
                "form": form,
                "form_change": rounded_delta(form, previous.get("form")),
                "selected_by_percent": selected_by_percent,
                "ownership_change": rounded_delta(
                    selected_by_percent,
                    previous.get("selected_by_percent"),
                ),
                "position": POSITIONS[player["element_type"]],
                "status": player.get("status", "a"),
                "news": player.get("news", ""),
                "chance_next": player.get("chance_of_playing_next_round"),
                "chance_this": player.get("chance_of_playing_this_round"),
                "transfers_in_event": player.get("transfers_in_event", 0),
                "transfers_out_event": player.get("transfers_out_event", 0),
                "value_form": as_float(player.get("value_form")),
                "value_season": as_float(player.get("value_season")),
            }
        )

    return players


def build_fixtures(fixtures, teams):
    team_lookup = {team["id"]: team for team in teams}
    result = []

    for fixture in fixtures:
        home = team_lookup.get(fixture["team_h"])
        away = team_lookup.get(fixture["team_a"])
        if not home or not away:
            continue

        result.append(
            {
                "id": fixture["id"],
                "event": fixture.get("event"),
                "kickoff_time": fixture.get("kickoff_time"),
                "finished": fixture.get("finished", False),
                "started": fixture.get("started", False),
                "home_team": home["name"],
                "home_slug": home["slug"],
                "away_team": away["name"],
                "away_slug": away["slug"],
                "home_score": fixture.get("team_h_score"),
                "away_score": fixture.get("team_a_score"),
            }
        )

    return result


def get_fixture_team_ids(fixtures):
    team_ids = set()
    for fixture in fixtures:
        team_ids.add(fixture["team_h"])
        team_ids.add(fixture["team_a"])
    return team_ids


def build_previous_player_lookup(previous_data):
    if not previous_data:
        return {}

    return {
        player["id"]: {
            "price": player["now_cost"] / 10,
            "form": as_float(player.get("form")),
            "selected_by_percent": as_float(player.get("selected_by_percent")),
        }
        for player in previous_data.get("elements", [])
    }


def get_current_event(data):
    current = next((event for event in data["events"] if event.get("is_current")), None)
    next_event = next((event for event in data["events"] if event.get("is_next")), None)
    selected = current or next_event or data["events"][0]

    return {
        "id": selected["id"],
        "name": selected["name"],
        "deadline": selected.get("deadline_time"),
        "is_current": selected.get("is_current", False),
        "is_next": selected.get("is_next", False),
    }


def build_events(data):
    return [
        {
            "id": event["id"],
            "name": event["name"],
            "deadline": event.get("deadline_time"),
            "is_current": event.get("is_current", False),
            "is_next": event.get("is_next", False),
            "finished": event.get("finished", False),
        }
        for event in data.get("events", [])
    ]


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def rounded_delta(current, previous):
    if previous is None:
        return None
    return round(current - previous, 2)


def slugify(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "okand"


if __name__ == "__main__":
    allsvenskan = get_allsvenskan_data()
    print(f"Hamtade {len(allsvenskan['players'])} spelare")
