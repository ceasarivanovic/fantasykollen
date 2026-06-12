POSITION_OPTIONS = ["MV", "Back", "Mittfält", "Anfall"]


def get_position_options():
    return POSITION_OPTIONS


def add_player_scores(player):
    return add_player_scores_with_fixture(player, None)


def add_player_scores_with_fixture(player, fixture_context=None):
    price = player["price"]
    form = player["form"]
    points_per_million = player["total_points"] / price if price else 0
    minutes_score = get_minutes_score(player["minutes"])
    availability_score = get_availability_score(player)
    market_score = get_market_score(player)
    differential_bonus = get_differential_bonus(player)
    risk_penalty = get_risk_penalty(player)
    fixture_factor = get_fixture_factor(fixture_context)
    fixture_impact = get_fixture_impact(fixture_factor)
    expected_points = get_expected_points(
        player,
        minutes_score,
        availability_score,
        risk_penalty,
        fixture_factor,
    )
    fixture_score = (fixture_factor - 1) * 8

    value_score = (
        (form * 1.9)
        + (player["points_per_game"] * 1.25)
        + (points_per_million * 0.9)
        + (minutes_score * 1.35)
        + (availability_score * 0.9)
        + (market_score * 0.35)
        + fixture_score
        - risk_penalty
    )
    captain_score = (
        (form * 2.1)
        + (player["points_per_game"] * 1.8)
        + (minutes_score * 1.4)
        + (availability_score * 1.2)
        + (fixture_score * 0.8)
        - (risk_penalty * 1.4)
    )
    differential_score = value_score + differential_bonus - (risk_penalty * 0.6)
    value_score = round(max(value_score, 0), 2)
    captain_score = round(max(captain_score, 0), 2)
    differential_score = round(max(differential_score, 0), 2)

    return {
        **player,
        "points_per_million": round(points_per_million, 2),
        "minutes_score": round(minutes_score, 2),
        "availability_score": round(availability_score, 2),
        "market_score": round(market_score, 2),
        "risk_penalty": round(risk_penalty, 2),
        "fixture_factor": round(fixture_factor, 2),
        "fixture_impact": fixture_impact,
        "next_fixture": fixture_context,
        "expected_points": round(expected_points, 1),
        "value_score": value_score,
        "captain_score": captain_score,
        "differential_score": differential_score,
        "value_label": get_value_label(value_score),
        "projection_label": get_projection_label(expected_points),
        "minutes_label": get_minutes_label(minutes_score),
        "risk_label": get_risk_label(risk_penalty),
        "decision_summary": get_decision_summary(value_score, expected_points, risk_penalty, minutes_score),
    }


def get_value_label(value_score):
    if value_score >= 40:
        return "Toppval"
    if value_score >= 32:
        return "Starkt val"
    if value_score >= 24:
        return "Intressant"
    if value_score >= 16:
        return "Håll koll"
    return "Svag signal"


def get_projection_label(expected_points):
    if expected_points >= 6:
        return "Hög prognos"
    if expected_points >= 4.5:
        return "Bra prognos"
    if expected_points >= 3:
        return "Okej prognos"
    return "Låg prognos"


def get_minutes_label(minutes_score):
    if minutes_score >= 4.4:
        return "Trygga minuter"
    if minutes_score >= 3.6:
        return "Ganska trygg"
    if minutes_score >= 2.7:
        return "Viss speltid"
    if minutes_score >= 1.6:
        return "Osäker roll"
    return "Mycket osäker"


def get_risk_label(risk_penalty):
    if risk_penalty >= 4:
        return "Hög risk"
    if risk_penalty >= 2:
        return "Viss risk"
    if risk_penalty > 0:
        return "Liten risk"
    return "Låg risk"


def get_decision_summary(value_score, expected_points, risk_penalty, minutes_score):
    if risk_penalty >= 4:
        return "Kontrollera status före deadline"
    if value_score >= 40 and expected_points >= 5 and minutes_score >= 3.6:
        return "Starkt köp om spelaren passar din budget"
    if value_score >= 32 and risk_penalty < 2:
        return "Bra alternativ att jämföra"
    if expected_points >= 5 and risk_penalty < 2:
        return "Intressant för omgången"
    if minutes_score < 2.7:
        return "Potential finns, men rollen är osäker"
    return "Jämför med alternativen"


def get_expected_points(player, minutes_score, availability_score, risk_penalty, fixture_factor=1):
    base = (player["points_per_game"] * 0.55) + (player["form"] * 0.35)
    minutes_multiplier = 0.72 + (minutes_score / 5 * 0.28)
    availability_multiplier = 0.55 + (availability_score / 5 * 0.45)
    risk_adjustment = max(0.55, 1 - (risk_penalty * 0.08))
    market_nudge = min(max(player["transfers_in_event"] - player["transfers_out_event"], 0) / 20000, 0.25)

    return max((base * minutes_multiplier * availability_multiplier * risk_adjustment * fixture_factor) + market_nudge, 0)


def get_fixture_factor(fixture_context):
    if not fixture_context:
        return 1

    difficulty_level = fixture_context["difficulty"]["level"]
    difficulty_factor = {
        1: 1.16,
        2: 1.09,
        3: 1.0,
        4: 0.92,
        5: 0.84,
    }.get(difficulty_level, 1)
    home_factor = 1.04 if fixture_context["venue"] == "H" else 0.97
    return difficulty_factor * home_factor


def get_fixture_impact(fixture_factor):
    percent = round((fixture_factor - 1) * 100)
    if percent >= 8:
        label = "Tydligt plus"
    elif percent >= 3:
        label = "Litet plus"
    elif percent <= -8:
        label = "Tydligt minus"
    elif percent <= -3:
        label = "Litet minus"
    else:
        label = "Neutral"

    return {
        "percent": percent,
        "label": label,
    }


def get_minutes_score(minutes):
    if minutes >= 900:
        return 5
    if minutes >= 650:
        return 4.4
    if minutes >= 450:
        return 3.6
    if minutes >= 270:
        return 2.7
    if minutes >= 90:
        return 1.6
    return 0.4


def get_availability_score(player):
    chance = player["chance_next"] or player["chance_this"]
    if chance is None:
        return 4.5 if player["status"] == "a" else 1.5
    return max(min(chance / 20, 5), 0)


def get_market_score(player):
    net_transfers = player["transfers_in_event"] - player["transfers_out_event"]
    if net_transfers <= 0:
        return 0
    if net_transfers >= 10000:
        return 5
    if net_transfers >= 5000:
        return 4
    if net_transfers >= 2500:
        return 3
    if net_transfers >= 1000:
        return 2
    return 1


def get_differential_bonus(player):
    ownership = player["selected_by_percent"]
    if ownership <= 3:
        return 3.0
    if ownership <= 7:
        return 2.2
    if ownership <= 12:
        return 1.4
    if ownership <= 20:
        return 0.6
    return 0


def get_risk_penalty(player):
    penalty = 0
    if player["status"] != "a":
        penalty += 3
    if player["news"]:
        penalty += 1.5

    chance = player["chance_next"] or player["chance_this"]
    if chance is not None:
        penalty += max(0, (100 - chance) / 20)

    if player["minutes"] < 90 and player["total_points"] > 0:
        penalty += 1.2

    return penalty


def build_dashboard(data):
    fixture_difficulty = get_fixture_difficulty(data)
    next_fixtures = get_next_fixture_by_team(data, fixture_difficulty)
    players = [
        add_player_scores_with_fixture(player, next_fixtures.get(player["team_slug"]))
        for player in data["players"]
    ]
    active_players = [player for player in players if player["price"] > 0]

    value_picks = sorted(
        [player for player in active_players if player["form"] > 0],
        key=lambda player: player["value_score"],
        reverse=True,
    )[:12]

    budget_picks = sorted(
        [player for player in active_players if player["price"] <= 7.0 and player["form"] > 0],
        key=lambda player: player["value_score"],
        reverse=True,
    )[:8]

    captain_picks = sorted(
        [
            player
            for player in active_players
            if player["form"] > 0 and player["risk_penalty"] < 2 and player["minutes"] >= 270
        ],
        key=lambda player: player["captain_score"],
        reverse=True,
    )[:6]

    projection_picks = sorted(
        [
            player
            for player in active_players
            if player["risk_penalty"] < 3 and player["minutes"] >= 270
        ],
        key=lambda player: player["expected_points"],
        reverse=True,
    )[:8]

    differentials = sorted(
        [
            player
            for player in active_players
            if player["selected_by_percent"] <= 10 and player["form"] > 0
        ],
        key=lambda player: player["differential_score"],
        reverse=True,
    )[:8]

    form_risers = sorted(
        [player for player in active_players if player["form_change"] and player["form_change"] > 0],
        key=lambda player: player["form_change"],
        reverse=True,
    )[:8]

    price_movers = sorted(
        [player for player in active_players if player["price_change"]],
        key=lambda player: abs(player["price_change"]),
        reverse=True,
    )[:8]

    ownership_risers = sorted(
        [
            player
            for player in active_players
            if player["ownership_change"] and player["ownership_change"] > 0
        ],
        key=lambda player: player["ownership_change"],
        reverse=True,
    )[:8]

    flagged_players = sorted(
        [player for player in active_players if player["status"] != "a" or player["news"]],
        key=lambda player: (player["risk_penalty"], player["selected_by_percent"]),
        reverse=True,
    )[:8]

    return {
        "value_picks": value_picks,
        "budget_picks": budget_picks,
        "captain_picks": captain_picks,
        "projection_picks": projection_picks,
        "differentials": differentials,
        "form_risers": form_risers,
        "price_movers": price_movers,
        "ownership_risers": ownership_risers,
        "flagged_players": flagged_players,
        "upcoming_fixtures": get_upcoming_fixtures(data, fixture_difficulty)[:10],
        "team_count": len(data["teams"]),
        "player_count": len(players),
        "average_price": round(sum(player["price"] for player in players) / len(players), 1),
        "has_history": any(player["form_change"] is not None for player in players),
    }


def build_gameweek_story(dashboard, event):
    top_value = dashboard["value_picks"][0] if dashboard["value_picks"] else None
    top_projection = dashboard["projection_picks"][0] if dashboard["projection_picks"] else None
    top_budget = dashboard["budget_picks"][0] if dashboard["budget_picks"] else None
    top_captain = dashboard["captain_picks"][0] if dashboard["captain_picks"] else None
    top_risk = dashboard["flagged_players"][0] if dashboard["flagged_players"] else None

    highlights = [
        item
        for item in [
            ("Bästa värde", top_value),
            ("Högst prognos", top_projection),
            ("Budgetfynd", top_budget),
            ("Kapten", top_captain),
        ]
        if item[1]
    ]

    if top_value and top_projection:
        intro = (
            f"Inför {event['name']} sticker {top_value['name']} ut i värdeindex, "
            f"medan {top_projection['name']} har starkast poängprognos. "
        )
    elif top_value:
        intro = f"Inför {event['name']} sticker {top_value['name']} ut som bästa värdeval. "
    else:
        intro = f"Inför {event['name']} samlar Fantasykollen de viktigaste signalerna från aktuell fantasydata. "

    if top_captain:
        intro += f"{top_captain['name']} är en av de tydligaste kaptenskandidaterna. "
    if top_budget:
        intro += f"Bland billigare spelare är {top_budget['name']} ett namn att jämföra. "
    if top_risk:
        intro += f"Kontrollera även statusen på {top_risk['name']} före deadline."

    return {
        "intro": intro,
        "highlights": highlights,
        "top_value": top_value,
        "top_projection": top_projection,
        "top_budget": top_budget,
        "top_captain": top_captain,
        "top_risk": top_risk,
    }


def filter_players(players_or_data, filters):
    if isinstance(players_or_data, dict):
        data = players_or_data
        fixture_difficulty = get_fixture_difficulty(data)
        next_fixtures = get_next_fixture_by_team(data, fixture_difficulty)
        scored_players = [
            add_player_scores_with_fixture(player, next_fixtures.get(player["team_slug"]))
            for player in data["players"]
        ]
    else:
        scored_players = [add_player_scores(player) for player in players_or_data]
    position = filters.get("position", "alla")
    team = filters.get("team", "alla")
    max_price = filters.get("max_price", "")
    sort_key = filters.get("sort", "value_score")

    if position != "alla":
        scored_players = [player for player in scored_players if player["position"] == position]

    if team != "alla":
        scored_players = [player for player in scored_players if player["team"] == team]

    if max_price:
        try:
            price_limit = float(max_price)
            scored_players = [player for player in scored_players if player["price"] <= price_limit]
        except ValueError:
            pass

    allowed_sort_keys = {
        "value_score",
        "form",
        "total_points",
        "price",
        "selected_by_percent",
        "points_per_million",
        "minutes_score",
        "risk_penalty",
        "market_score",
    }
    if sort_key not in allowed_sort_keys:
        sort_key = "value_score"

    return sorted(scored_players, key=lambda player: player[sort_key], reverse=True)


def get_player_profile(data, slug):
    fixture_difficulty = get_fixture_difficulty(data)
    next_fixtures = get_next_fixture_by_team(data, fixture_difficulty)
    players = [
        add_player_scores_with_fixture(player, next_fixtures.get(player["team_slug"]))
        for player in data["players"]
    ]
    player = next((item for item in players if item["slug"] == slug), None)
    if not player:
        return None

    rankings = get_player_rankings(players, player)
    position_average = get_position_average(players, player["position"])
    recommendation = get_player_recommendation(player, rankings, position_average)

    teammates = sorted(
        [
            item
            for item in players
            if item["team"] == player["team"] and item["id"] != player["id"]
        ],
        key=lambda item: item["value_score"],
        reverse=True,
    )[:8]

    similar = sorted(
        [
            item
            for item in players
            if item["position"] == player["position"] and item["id"] != player["id"]
        ],
        key=lambda item: abs(item["price"] - player["price"]) + abs(item["value_score"] - player["value_score"]) / 10,
    )[:8]
    category_links = get_player_category_links(player)

    return {
        "player": player,
        "rankings": rankings,
        "position_average": position_average,
        "recommendation": recommendation,
        "teammates": teammates,
        "similar": similar,
        "category_links": category_links,
    }


def get_player_category_links(player):
    links = []
    if player["price"] <= 7.0 and player["value_score"] >= 20:
        links.append(
            {
                "label": "Budgetfynd",
                "slug": "budgetfynd",
                "reason": "Lågt pris och intressant värdeindex.",
            }
        )
    if player["captain_score"] >= 30 and player["risk_penalty"] < 2:
        links.append(
            {
                "label": "Kaptenskandidat",
                "slug": "kaptener",
                "reason": "Hög prognos med relativt låg risk.",
            }
        )
    if player["selected_by_percent"] <= 10 and player["differential_score"] >= 20:
        links.append(
            {
                "label": "Differential",
                "slug": "differentials",
                "reason": "Låg ägarandel med uppsida.",
            }
        )
    return links


def get_player_rankings(players, player):
    overall = sorted(players, key=lambda item: item["value_score"], reverse=True)
    team = sorted(
        [item for item in players if item["team"] == player["team"]],
        key=lambda item: item["value_score"],
        reverse=True,
    )
    position = sorted(
        [item for item in players if item["position"] == player["position"]],
        key=lambda item: item["value_score"],
        reverse=True,
    )

    return {
        "overall": next(index for index, item in enumerate(overall, start=1) if item["id"] == player["id"]),
        "team": next(index for index, item in enumerate(team, start=1) if item["id"] == player["id"]),
        "position": next(index for index, item in enumerate(position, start=1) if item["id"] == player["id"]),
        "overall_count": len(overall),
        "team_count": len(team),
        "position_count": len(position),
    }


def get_position_average(players, position):
    position_players = [item for item in players if item["position"] == position]
    if not position_players:
        return {}

    return {
        "price": round(sum(item["price"] for item in position_players) / len(position_players), 1),
        "form": round(sum(item["form"] for item in position_players) / len(position_players), 1),
        "expected_points": round(sum(item["expected_points"] for item in position_players) / len(position_players), 1),
        "value_score": round(sum(item["value_score"] for item in position_players) / len(position_players), 1),
    }


def get_player_recommendation(player, rankings, position_average):
    if player["risk_penalty"] >= 3:
        return {
            "label": "Undvik",
            "tone": "danger",
            "confidence": "Låg trygghet",
            "action": "Vänta tills statusen är tydligare.",
            "reason": "Risken är förhöjd. Kontrollera status och nyheter innan du väljer spelaren.",
        }

    if player["minutes"] < 270 and player["total_points"] > 0:
        return {
            "label": "Håll koll",
            "tone": "watch",
            "confidence": "Osäker roll",
            "action": "Bevaka minuter och startchans.",
            "reason": "Signalerna finns, men speltiden är inte tillräckligt trygg ännu.",
        }

    above_position = player["value_score"] >= position_average.get("value_score", 0)
    strong_projection = player["expected_points"] >= position_average.get("expected_points", 0) + 0.5

    if above_position and strong_projection and player["risk_penalty"] < 2:
        return {
            "label": "Köp",
            "tone": "buy",
            "confidence": "Hög trygghet",
            "action": "Bra köp om priset passar din trupp.",
            "reason": "Spelaren ligger över positionssnittet och har stark prognos med låg risk.",
        }

    if above_position or player["selected_by_percent"] <= 10:
        return {
            "label": "Håll koll",
            "tone": "watch",
            "confidence": "Medeltrygg",
            "action": "Jämför mot liknande spelare innan byte.",
            "reason": "Spelaren har intressanta signaler, men behöver jämföras mot alternativen.",
        }

    return {
        "label": "Avvakta",
        "tone": "neutral",
        "confidence": "Neutral",
        "action": "Inte prioriterad just nu.",
        "reason": "Spelaren sticker inte ut tillräckligt jämfört med andra alternativ just nu.",
    }


def get_team_profile(data, slug):
    team = next((item for item in data["teams"] if item["slug"] == slug), None)
    if not team:
        return None

    fixture_difficulty = get_fixture_difficulty(data)
    next_fixtures = get_next_fixture_by_team(data, fixture_difficulty)
    players = [
        add_player_scores_with_fixture(player, next_fixtures.get(player["team_slug"]))
        for player in data["players"]
        if player["team_slug"] == slug
    ]
    players_by_value = sorted(players, key=lambda player: player["value_score"], reverse=True)
    players_by_points = sorted(players, key=lambda player: player["total_points"], reverse=True)
    regulars = sorted(players, key=lambda player: player["minutes"], reverse=True)
    league_table = get_league_table(data)
    table_position = next(
        (
            {"position": index, **row}
            for index, row in enumerate(league_table, start=1)
            if row["slug"] == slug
        ),
        None,
    )
    latest_results = get_latest_team_results(data, slug)
    position_groups = get_team_position_groups(players)

    return {
        "team": team,
        "table_position": table_position,
        "latest_results": latest_results,
        "players": players_by_value,
        "top_value": players_by_value[:10],
        "top_points": players_by_points[:6],
        "regulars": regulars[:6],
        "position_groups": position_groups,
        "buy_candidates": players_by_value[:4],
        "watch_candidates": sorted(
            [player for player in players if player["selected_by_percent"] <= 10 and player["risk_penalty"] < 3],
            key=lambda player: player["value_score"],
            reverse=True,
        )[:4],
        "risk_candidates": sorted(
            [player for player in players if player["risk_penalty"] > 0 or player["news"]],
            key=lambda player: (player["risk_penalty"], player["selected_by_percent"]),
            reverse=True,
        )[:4],
        "fixtures": [
            fixture
            for fixture in get_upcoming_fixtures(data, get_fixture_difficulty(data))
            if fixture["home_slug"] == slug or fixture["away_slug"] == slug
        ][:6],
        "squad_form": round(sum(player["form"] for player in players) / len(players), 2) if players else 0,
        "fantasy_points": sum(player["total_points"] for player in players),
        "average_price": round(sum(player["price"] for player in players) / len(players), 1) if players else 0,
    }


def get_team_position_groups(players):
    groups = {}
    for position in POSITION_OPTIONS:
        ranked = sorted(
            [player for player in players if player["position"] == position],
            key=lambda player: player["value_score"],
            reverse=True,
        )
        if ranked:
            groups[position] = ranked[:3]
    return groups


def get_latest_team_results(data, slug):
    results = []
    finished = [
        fixture
        for fixture in data.get("fixtures", [])
        if fixture["finished"]
        and (fixture["home_slug"] == slug or fixture["away_slug"] == slug)
        and fixture["home_score"] is not None
        and fixture["away_score"] is not None
    ]

    for fixture in sorted(finished, key=lambda item: (item["event"], item["kickoff_time"] or ""), reverse=True)[:5]:
        is_home = fixture["home_slug"] == slug
        goals_for = fixture["home_score"] if is_home else fixture["away_score"]
        goals_against = fixture["away_score"] if is_home else fixture["home_score"]
        opponent = fixture["away_team"] if is_home else fixture["home_team"]
        opponent_slug = fixture["away_slug"] if is_home else fixture["home_slug"]
        if goals_for > goals_against:
            result = "V"
        elif goals_for < goals_against:
            result = "F"
        else:
            result = "O"

        results.append(
            {
                "result": result,
                "venue": "H" if is_home else "B",
                "opponent": opponent,
                "opponent_slug": opponent_slug,
                "score": f"{goals_for}-{goals_against}",
                "event": fixture["event"],
            }
        )

    return results


def get_league_table(data):
    table = {
        team["slug"]: {
            **team,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
        }
        for team in data["teams"]
    }

    for fixture in data.get("fixtures", []):
        if not fixture["finished"]:
            continue
        if fixture["home_score"] is None or fixture["away_score"] is None:
            continue
        if fixture["home_slug"] not in table or fixture["away_slug"] not in table:
            continue

        home = table[fixture["home_slug"]]
        away = table[fixture["away_slug"]]
        home_goals = fixture["home_score"]
        away_goals = fixture["away_score"]

        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += home_goals
        home["goals_against"] += away_goals
        away["goals_for"] += away_goals
        away["goals_against"] += home_goals

        if home_goals > away_goals:
            home["wins"] += 1
            home["points"] += 3
            away["losses"] += 1
        elif home_goals < away_goals:
            away["wins"] += 1
            away["points"] += 3
            home["losses"] += 1
        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    for team in table.values():
        team["goal_difference"] = team["goals_for"] - team["goals_against"]

    return sorted(
        table.values(),
        key=lambda team: (
            team["points"],
            team["goal_difference"],
            team["goals_for"],
            team["name"],
        ),
        reverse=True,
    )


def get_fixture_strength(data):
    teams = data["teams"]
    players = data["players"]
    strength_by_team = {}

    for team in teams:
        team_players = [player for player in players if player["team"] == team["name"]]
        if not team_players:
            continue

        form = sum(player["form"] for player in team_players) / len(team_players)
        points = sum(player["total_points"] for player in team_players)
        strength_by_team[team["name"]] = {
            **team,
            "squad_form": round(form, 2),
            "fantasy_points": points,
        }

    return sorted(
        strength_by_team.values(),
        key=lambda team: (team["fantasy_points"], team["squad_form"]),
        reverse=True,
    )


def get_fixture_difficulty(data):
    strength = get_fixture_strength(data)
    if not strength:
        return {}

    max_points = max(team["fantasy_points"] for team in strength) or 1
    difficulty = {}

    for team in strength:
        raw = (team["fantasy_points"] / max_points) * 4 + (team["squad_form"] / 10)
        if raw >= 3.8:
            level = 5
            label = "Svår"
        elif raw >= 3.0:
            level = 4
            label = "Tuff"
        elif raw >= 2.2:
            level = 3
            label = "Neutral"
        elif raw >= 1.4:
            level = 2
            label = "Bra"
        else:
            level = 1
            label = "Mycket bra"

        difficulty[team["slug"]] = {
            "level": level,
            "label": label,
            "score": round(raw, 2),
        }

    return difficulty


def get_upcoming_fixtures(data, difficulty):
    upcoming = []

    for fixture in data.get("fixtures", []):
        if fixture["finished"] or fixture["event"] is None:
            continue

        home_difficulty = difficulty.get(fixture["away_slug"], {"level": 3, "label": "Neutral"})
        away_difficulty = difficulty.get(fixture["home_slug"], {"level": 3, "label": "Neutral"})
        upcoming.append(
            {
                **fixture,
                "home_difficulty": home_difficulty,
                "away_difficulty": away_difficulty,
            }
        )

    return sorted(upcoming, key=lambda fixture: (fixture["event"], fixture["kickoff_time"] or ""))


def get_next_fixture_by_team(data, difficulty):
    next_by_team = {}

    for fixture in get_upcoming_fixtures(data, difficulty):
        home_context = {
            "event": fixture["event"],
            "kickoff_time": fixture["kickoff_time"],
            "venue": "H",
            "opponent": fixture["away_team"],
            "opponent_slug": fixture["away_slug"],
            "difficulty": fixture["home_difficulty"],
        }
        away_context = {
            "event": fixture["event"],
            "kickoff_time": fixture["kickoff_time"],
            "venue": "B",
            "opponent": fixture["home_team"],
            "opponent_slug": fixture["home_slug"],
            "difficulty": fixture["away_difficulty"],
        }

        next_by_team.setdefault(fixture["home_slug"], home_context)
        next_by_team.setdefault(fixture["away_slug"], away_context)

    return next_by_team
