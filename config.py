from dotenv import load_dotenv
from pathlib import Path
import os


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
CORS_ORIGINS = os.environ["CORS_ORIGINS"].split(",")
API_GLOBAL_KEY = os.environ["API_GLOBAL_KEY"]
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
AUTO_REFRESH_HOURS = int(os.environ["AUTO_REFRESH_HOURS"])
REQUEST_TIMEOUT = int(os.environ["REQUEST_TIMEOUT"])


APP_TITLE = "Sportox NBA Data API"
APP_DESCRIPTION = (
    "API pública para consultar datos NBA ya cacheados en MongoDB: equipos, "
    "jugadores, lesiones, lineups y ATS."
)


TEAM_STAT_SOURCES = [
    {"metric_key": "points_per_game", "metric_label": "Points per Game", "url": "https://www.teamrankings.com/nba/stat/points-per-game"},
    {"metric_key": "first_quarter_points_per_game", "metric_label": "1st Quarter Points per Game", "url": "https://www.teamrankings.com/nba/stat/1st-quarter-points-per-game"},
    {"metric_key": "second_quarter_points_per_game", "metric_label": "2nd Quarter Points per Game", "url": "https://www.teamrankings.com/nba/stat/2nd-quarter-points-per-game"},
    {"metric_key": "first_half_points_per_game", "metric_label": "1st Half Points per Game", "url": "https://www.teamrankings.com/nba/stat/1st-half-points-per-game"},
    {"metric_key": "average_scoring_margin", "metric_label": "Average Scoring Margin", "url": "https://www.teamrankings.com/nba/stat/average-scoring-margin"},
    {"metric_key": "average_first_quarter_margin", "metric_label": "Average 1st Quarter Margin", "url": "https://www.teamrankings.com/nba/stat/average-1st-quarter-margin"},
    {"metric_key": "average_second_quarter_margin", "metric_label": "Average 2nd Quarter Margin", "url": "https://www.teamrankings.com/nba/stat/average-2nd-quarter-margin"},
    {"metric_key": "average_first_half_margin", "metric_label": "Average 1st Half Margin", "url": "https://www.teamrankings.com/nba/stat/average-1st-half-margin"},
    {"metric_key": "points_from_two_pointers", "metric_label": "Points from 2 Pointers", "url": "https://www.teamrankings.com/nba/stat/points-from-2-pointers"},
    {"metric_key": "points_from_three_pointers", "metric_label": "Points from 3 Pointers", "url": "https://www.teamrankings.com/nba/stat/points-from-3-pointers"},
    {"metric_key": "offensive_efficiency", "metric_label": "Offensive Efficiency", "url": "https://www.teamrankings.com/nba/stat/offensive-efficiency"},
    {"metric_key": "fastbreak_efficiency", "metric_label": "Fastbreak Efficiency", "url": "https://www.teamrankings.com/nba/stat/fastbreak-efficiency"},
    {"metric_key": "average_biggest_lead", "metric_label": "Average Biggest Lead", "url": "https://www.teamrankings.com/nba/stat/average-biggest-lead"},
    {"metric_key": "opponent_points_per_game", "metric_label": "Opponent Points per Game", "url": "https://www.teamrankings.com/nba/stat/opponent-points-per-game"},
    {"metric_key": "opponent_first_quarter_points_per_game", "metric_label": "Opponent 1st Quarter Points per Game", "url": "https://www.teamrankings.com/nba/stat/opponent-1st-quarter-points-per-game"},
    {"metric_key": "opponent_second_quarter_points_per_game", "metric_label": "Opponent 2nd Quarter Points per Game", "url": "https://www.teamrankings.com/nba/stat/opponent-2nd-quarter-points-per-game"},
    {"metric_key": "opponent_first_half_points_per_game", "metric_label": "Opponent 1st Half Points per Game", "url": "https://www.teamrankings.com/nba/stat/opponent-1st-half-points-per-game"},
    {"metric_key": "defensive_efficiency", "metric_label": "Defensive Efficiency", "url": "https://www.teamrankings.com/nba/stat/defensive-efficiency"},
    {"metric_key": "opponent_fastbreak_efficiency", "metric_label": "Opponent Fastbreak Efficiency", "url": "https://www.teamrankings.com/nba/stat/opponent-fastbreak-efficiency"},
    {"metric_key": "opponent_average_biggest_lead", "metric_label": "Opponent Average Biggest Lead", "url": "https://www.teamrankings.com/nba/stat/opponent-average-biggest-lead"},
]


PLAYER_STAT_SOURCES = [
    {"metric_key": "points", "metric_label": "Points", "url": "https://www.teamrankings.com/nba/player-stat/points"},
    {"metric_key": "assists", "metric_label": "Assists", "url": "https://www.teamrankings.com/nba/player-stat/assists"},
    {"metric_key": "offensive_rebounds", "metric_label": "Offensive Rebounds", "url": "https://www.teamrankings.com/nba/player-stat/rebounds-offensive"},
    {"metric_key": "defensive_rebounds", "metric_label": "Defensive Rebounds", "url": "https://www.teamrankings.com/nba/player-stat/rebounds-defensive"},
    {"metric_key": "steals", "metric_label": "Steals", "url": "https://www.teamrankings.com/nba/player-stat/steals"},
    {"metric_key": "blocks", "metric_label": "Blocks", "url": "https://www.teamrankings.com/nba/player-stat/blocks"},
    {"metric_key": "personal_fouls", "metric_label": "Personal Fouls", "url": "https://www.teamrankings.com/nba/player-stat/fouls-personal"},
]


ATS_TEAM_SLUGS = {
    "Atlanta Hawks": "atlanta-hawks",
    "Boston Celtics": "boston-celtics",
    "Brooklyn Nets": "brooklyn-nets",
    "Charlotte Hornets": "charlotte-hornets",
    "Chicago Bulls": "chicago-bulls",
    "Cleveland Cavaliers": "cleveland-cavaliers",
    "Dallas Mavericks": "dallas-mavericks",
    "Denver Nuggets": "denver-nuggets",
    "Detroit Pistons": "detroit-pistons",
    "Golden State Warriors": "golden-state-warriors",
    "Houston Rockets": "houston-rockets",
    "Indiana Pacers": "indiana-pacers",
    "Los Angeles Clippers": "los-angeles-clippers",
    "Los Angeles Lakers": "los-angeles-lakers",
    "Memphis Grizzlies": "memphis-grizzlies",
    "Miami Heat": "miami-heat",
    "Milwaukee Bucks": "milwaukee-bucks",
    "Minnesota Timberwolves": "minnesota-timberwolves",
    "New Orleans Pelicans": "new-orleans-pelicans",
    "New York Knicks": "new-york-knicks",
    "Oklahoma City Thunder": "oklahoma-city-thunder",
    "Orlando Magic": "orlando-magic",
    "Philadelphia 76ers": "philadelphia-76ers",
    "Phoenix Suns": "phoenix-suns",
    "Portland Trail Blazers": "portland-trail-blazers",
    "Sacramento Kings": "sacramento-kings",
    "San Antonio Spurs": "san-antonio-spurs",
    "Toronto Raptors": "toronto-raptors",
    "Utah Jazz": "utah-jazz",
    "Washington Wizards": "washington-wizards",
}


ATS_SOURCES = [
    {
        "team": team_name,
        "url": f"https://www.teamrankings.com/nba/team/{slug}/ats-results",
    }
    for team_name, slug in ATS_TEAM_SLUGS.items()
]


INJURIES_URL = "https://espndeportes.espn.com/basquetbol/nba/lesiones"
LINEUPS_URL_TEMPLATE = "https://stats.nba.com/js/data/leaders/00_daily_lineups_{date_key}.json"


DATASET_LABELS = {
    "teams": "Estadísticas de equipos",
    "players": "Estadísticas de jugadores",
    "injuries": "Lesiones",
    "lineups": "Lineups diarios",
    "ats": "Resultados ATS",
}