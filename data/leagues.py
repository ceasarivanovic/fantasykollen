LEAGUES = {
    "allsvenskan": {
        "id": "allsvenskan",
        "name": "Fantasy Allsvenskan",
        "short_name": "Allsvenskan",
        "country": "Sverige",
        "status": "active",
        "description": "Fantasykollens första liga med spelarvärde, form, speltid och matchsvårighet.",
    },
    "premier-league": {
        "id": "premier-league",
        "name": "Fantasy Premier League",
        "short_name": "Premier League",
        "country": "England",
        "status": "planned",
        "description": "Planerad liga för framtida jämförelser, spelaranalys och värdeindex.",
    },
    "vm": {
        "id": "vm",
        "name": "VM Fantasy",
        "short_name": "VM",
        "country": "Internationellt",
        "status": "planned",
        "description": "Planerad turneringsvy om ett populärt fantasyspel finns tillgängligt.",
    },
}

ACTIVE_LEAGUE_ID = "allsvenskan"


def get_active_league():
    return LEAGUES[ACTIVE_LEAGUE_ID]


def get_leagues():
    return list(LEAGUES.values())
