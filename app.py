import os
from datetime import date, datetime

from flask import Flask, Response, redirect, render_template, request, url_for

from analysis.fantasy import (
    build_gameweek_story,
    build_dashboard,
    filter_players,
    get_fixture_strength,
    get_league_table,
    get_player_profile,
    get_position_options,
    get_team_profile,
)
from data.fetcher import get_allsvenskan_data, refresh_allsvenskan_data
from data.leagues import get_active_league, get_leagues

POSITION_SLUGS = {
    "malvakter": "MV",
    "backar": "Back",
    "mittfaltare": "Mittfält",
    "anfallare": "Anfall",
}
POSITION_LABELS = {
    "MV": "målvakter",
    "Back": "backar",
    "Mittfält": "mittfältare",
    "Anfall": "anfallare",
}


def create_app():
    app = Flask(__name__)
    app.config["SITE_URL"] = os.getenv("SITE_URL", "").rstrip("/")
    app.config["PLAUSIBLE_DOMAIN"] = os.getenv("PLAUSIBLE_DOMAIN", "")
    app.config["GA_MEASUREMENT_ID"] = os.getenv("GA_MEASUREMENT_ID", "")

    @app.context_processor
    def inject_global_context():
        return {
            "active_league": get_active_league(),
            "available_leagues": get_leagues(),
            "site_url": app.config["SITE_URL"],
            "plausible_domain": app.config["PLAUSIBLE_DOMAIN"],
            "ga_measurement_id": app.config["GA_MEASUREMENT_ID"],
        }

    @app.template_filter("friendly_datetime")
    def friendly_datetime(value):
        if not value:
            return "Okänd tid"
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
        return parsed.strftime("%Y-%m-%d %H:%M")

    @app.cli.command("refresh-data")
    def refresh_data_command():
        data = refresh_allsvenskan_data()
        print(
            f"Uppdaterade Fantasykollen: {len(data['teams'])} lag, "
            f"{len(data['players'])} spelare, källa {data['meta']['source']}"
        )

    @app.route("/")
    def home():
        data = get_allsvenskan_data()
        dashboard = build_dashboard(data)
        story = build_gameweek_story(dashboard, data["event"])
        return render_template("home.html", data=data, dashboard=dashboard, story=story)

    @app.route("/allsvenskan")
    def allsvenskan():
        data = get_allsvenskan_data()
        fixture_strength = get_fixture_strength(data)
        league_table = get_league_table(data)
        return render_template(
            "league.html",
            data=data,
            fixture_strength=fixture_strength,
            league_table=league_table,
        )

    @app.route("/fantasy")
    def fantasy():
        data = get_allsvenskan_data()
        dashboard = build_dashboard(data)
        return render_template("fantasy.html", data=data, dashboard=dashboard)

    @app.route("/tips/<category>")
    def tips_category(category):
        data = get_allsvenskan_data()
        dashboard = build_dashboard(data)
        categories = {
            "budgetfynd": {
                "title": "Budgetfynd i Fantasy Allsvenskan",
                "heading": "Budgetfynd i Fantasy Allsvenskan",
                "eyebrow": "Budget",
                "description": "Prisvärda spelare under 7.0M med starka signaler inför nästa omgång.",
                "players": dashboard["budget_picks"],
                "seo": "Hitta billiga spelare, budgetfynd och prisvärda val i Fantasy Allsvenskan.",
                "angle": "Budgetfynd passar när du behöver frigöra pengar utan att tappa för mycket prognos. Modellen prioriterar lågt pris, rimlig speltid och bra värdeindex.",
                "metric_label": "Index",
                "metric_key": "value_score",
                "primary_cta": "Jämför alla spelare",
                "primary_endpoint": "players",
            },
            "kaptener": {
                "title": "Kaptenskandidater i Fantasy Allsvenskan",
                "heading": "Kaptenskandidater i Fantasy Allsvenskan",
                "eyebrow": "Kapten",
                "description": "Tryggare kaptensval baserat på prognos, form, speltid och risk.",
                "players": dashboard["captain_picks"],
                "seo": "Jämför kaptenskandidater inför nästa omgång i Fantasy Allsvenskan.",
                "angle": "Kaptensval bör vara mer konservativa än vanliga chansningar. Här väger prognos, trygg speltid, form och låg risk extra tungt.",
                "metric_label": "Kapten",
                "metric_key": "captain_score",
                "primary_cta": "Se fantasycentret",
                "primary_endpoint": "fantasy",
            },
            "differentials": {
                "title": "Differentials i Fantasy Allsvenskan",
                "heading": "Differentials i Fantasy Allsvenskan",
                "eyebrow": "Låg ägarandel",
                "description": "Lågägda spelare med potential att ge dig fördel mot resten av ligan.",
                "players": dashboard["differentials"],
                "seo": "Hitta lågägda spelare och differentials i Fantasy Allsvenskan.",
                "angle": "Differentials är spelare med lägre ägarandel som ändå har tillräcklig uppsida. De är bäst när du behöver jaga placering, inte när du vill spela helt säkert.",
                "metric_label": "Diff",
                "metric_key": "differential_score",
                "primary_cta": "Se alla spelare",
                "primary_endpoint": "players",
            },
        }
        config = categories.get(category)
        if not config:
            return render_template("404.html"), 404
        return render_template(
            "tips_category.html",
            data=data,
            dashboard=dashboard,
            category=category,
            config=config,
        )

    @app.route("/omgang")
    def current_gameweek():
        data = get_allsvenskan_data()
        return redirect(url_for("gameweek", event_id=data["event"]["id"]))

    @app.route("/omgang/<int:event_id>")
    def gameweek(event_id):
        data = get_allsvenskan_data()
        dashboard = build_dashboard(data)
        event = next((item for item in data["events"] if item["id"] == event_id), None)
        if not event:
            event = {
                **data["event"],
                "id": event_id,
                "name": f"Omgång {event_id}",
            }
        story = build_gameweek_story(dashboard, event)
        return render_template(
            "gameweek.html",
            data=data,
            dashboard=dashboard,
            event=event,
            story=story,
        )

    @app.route("/spelare")
    def players():
        data = get_allsvenskan_data()
        per_page = 40
        page = request.args.get("page", 1, type=int)
        page = max(page, 1)
        filters = {
            "position": request.args.get("position", "alla"),
            "team": request.args.get("team", "alla"),
            "max_price": request.args.get("max_price", ""),
            "sort": request.args.get("sort", "value_score"),
        }
        players = filter_players(data, filters)
        total_players = len(players)
        total_pages = max((total_players + per_page - 1) // per_page, 1)
        page = min(page, total_pages)
        start = (page - 1) * per_page
        end = start + per_page
        visible_players = players[start:end]
        return render_template(
            "players.html",
            data=data,
            players=visible_players,
            pagination={
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "total_players": total_players,
                "start": start + 1 if total_players else 0,
                "end": min(end, total_players),
                "has_prev": page > 1,
                "has_next": page < total_pages,
            },
            filters=filters,
            positions=get_position_options(),
        )

    @app.route("/position/<slug>")
    def position_landing(slug):
        position = POSITION_SLUGS.get(slug)
        if not position:
            return render_template("404.html"), 404
        data = get_allsvenskan_data()
        players = filter_players(data, {"position": position, "team": "alla", "max_price": "", "sort": "value_score"})
        label = POSITION_LABELS[position]
        return render_template(
            "seo_landing.html",
            data=data,
            players=players[:24],
            title=f"Bästa {label} i Fantasy Allsvenskan",
            heading=f"Bästa {label} i Fantasy Allsvenskan",
            eyebrow="Position",
            description=f"Jämför {label} efter värdeindex, prognos, speltid, risk och nästa match.",
            canonical_url=url_for("position_landing", slug=slug, _external=True),
        )

    @app.route("/pris/under-7m")
    def price_under_7():
        data = get_allsvenskan_data()
        players = filter_players(data, {"position": "alla", "team": "alla", "max_price": "7.0", "sort": "value_score"})
        return render_template(
            "seo_landing.html",
            data=data,
            players=players[:24],
            title="Spelare under 7.0M i Fantasy Allsvenskan",
            heading="Spelare under 7.0M i Fantasy Allsvenskan",
            eyebrow="Pris",
            description="Hitta prisvärda fantasyspelare under 7.0M med bra form, speltid och värdeindex.",
            canonical_url=url_for("price_under_7", _external=True),
        )

    @app.route("/lag/<slug>/budgetfynd")
    def team_budget_picks(slug):
        data = get_allsvenskan_data()
        profile = get_team_profile(data, slug)
        if not profile:
            return render_template("404.html"), 404
        players = [
            player
            for player in profile["players"]
            if player["price"] <= 7.0 and player["risk_penalty"] < 3
        ][:24]
        return render_template(
            "seo_landing.html",
            data=data,
            players=players,
            title=f"Budgetfynd i {profile['team']['name']} - Fantasy Allsvenskan",
            heading=f"Budgetfynd i {profile['team']['name']}",
            eyebrow="Lag",
            description=f"Prisvärda spelare i {profile['team']['name']} inför kommande omgångar.",
            canonical_url=url_for("team_budget_picks", slug=slug, _external=True),
        )

    @app.route("/spelare/<slug>")
    def player_detail(slug):
        data = get_allsvenskan_data()
        profile = get_player_profile(data, slug)
        if not profile:
            return render_template("404.html"), 404
        return render_template("player_detail.html", data=data, profile=profile)

    @app.route("/lag/<slug>")
    def team_detail(slug):
        data = get_allsvenskan_data()
        profile = get_team_profile(data, slug)
        if not profile:
            return render_template("404.html"), 404
        return render_template("team_detail.html", data=data, profile=profile)

    @app.route("/metodik")
    def methodology():
        return render_template("methodology.html")

    @app.route("/om")
    def about():
        return render_template("about.html")

    @app.route("/kontakt")
    def contact():
        return render_template("contact.html")

    @app.route("/integritet")
    def privacy():
        return render_template("privacy.html")

    @app.route("/robots.txt")
    def robots():
        lines = [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {url_for('sitemap', _external=True)}",
        ]
        return Response("\n".join(lines), mimetype="text/plain")

    @app.route("/sitemap.xml")
    def sitemap():
        data = get_allsvenskan_data()
        scored_dashboard = build_dashboard(data)
        pages = [
            ("home", "daily", "1.0"),
            ("fantasy", "daily", "0.9"),
            ("gameweek", "daily", "0.9"),
            ("tips_category", "daily", "0.8"),
            ("players", "daily", "0.8"),
            ("allsvenskan", "weekly", "0.7"),
            ("methodology", "monthly", "0.7"),
            ("about", "monthly", "0.5"),
            ("contact", "monthly", "0.4"),
            ("privacy", "monthly", "0.3"),
            ("price_under_7", "daily", "0.8"),
        ]
        urls = []
        today = date.today().isoformat()

        for endpoint, changefreq, priority in pages:
            if endpoint == "tips_category":
                category_urls = ["budgetfynd", "kaptener", "differentials"]
                for category in category_urls:
                    urls.append(
                        f"""
                        <url>
                            <loc>{url_for(endpoint, category=category, _external=True)}</loc>
                            <lastmod>{today}</lastmod>
                            <changefreq>{changefreq}</changefreq>
                            <priority>{priority}</priority>
                        </url>
                        """
                    )
            elif endpoint == "position_landing":
                pass
            else:
                kwargs = {"event_id": data["event"]["id"]} if endpoint == "gameweek" else {}
                urls.append(
                    f"""
                    <url>
                        <loc>{url_for(endpoint, _external=True, **kwargs)}</loc>
                        <lastmod>{today}</lastmod>
                        <changefreq>{changefreq}</changefreq>
                        <priority>{priority}</priority>
                    </url>
                    """
                )

        for slug in POSITION_SLUGS:
            urls.append(
                f"""
                <url>
                    <loc>{url_for('position_landing', slug=slug, _external=True)}</loc>
                    <lastmod>{today}</lastmod>
                    <changefreq>daily</changefreq>
                    <priority>0.8</priority>
                </url>
                """
            )

        for team in data["teams"]:
            urls.append(
                f"""
                <url>
                    <loc>{url_for('team_detail', slug=team['slug'], _external=True)}</loc>
                    <lastmod>{today}</lastmod>
                    <changefreq>weekly</changefreq>
                    <priority>0.7</priority>
                </url>
                """
            )
            urls.append(
                f"""
                <url>
                    <loc>{url_for('team_budget_picks', slug=team['slug'], _external=True)}</loc>
                    <lastmod>{today}</lastmod>
                    <changefreq>daily</changefreq>
                    <priority>0.7</priority>
                </url>
                """
            )

        sitemap_players = sorted(
            scored_dashboard["value_picks"] + scored_dashboard["captain_picks"],
            key=lambda player: player["value_score"],
            reverse=True,
        )
        seen = set()
        for player in sitemap_players:
            if player["slug"] in seen:
                continue
            seen.add(player["slug"])
            urls.append(
                f"""
                <url>
                    <loc>{url_for('player_detail', slug=player['slug'], _external=True)}</loc>
                    <lastmod>{today}</lastmod>
                    <changefreq>daily</changefreq>
                    <priority>0.8</priority>
                </url>
                """
            )

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            {''.join(urls)}
        </urlset>
        """
        return Response(xml, mimetype="application/xml")

    return app


app = create_app()


if __name__ == "__main__":
    print("Startar Fantasykollen...")
    app.run(debug=True)
