from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import StringIO
from threading import Lock
from typing import Any, Dict, List, Optional
import logging
import re

from bs4 import BeautifulSoup
import pandas as pd
from pymongo import MongoClient
import requests

from config import (
    ATS_SOURCES,
    DATASET_LABELS,
    DB_NAME,
    INJURIES_URL,
    LINEUPS_URL_TEMPLATE,
    MONGO_URL,
    PLAYER_STAT_SOURCES,
    REQUEST_TIMEOUT,
    TEAM_STAT_SOURCES,
)


logger = logging.getLogger(__name__)
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]
datasets_collection = db.cached_datasets
logs_collection = db.update_logs
refresh_lock = Lock()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        }
    )
    return session


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if value == "":
        return None
    return value


def normalize_column_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower())
    return value.strip("_")


def read_first_table(html: str) -> pd.DataFrame:
    tables = pd.read_html(StringIO(html))
    if not tables:
        raise ValueError("No se encontraron tablas HTML")
    return tables[0].fillna("")


def fetch_html(url: str, extra_headers: Optional[Dict[str, str]] = None) -> str:
    session = create_session()
    headers = extra_headers or {}
    response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def parse_team_metric(source: Dict[str, str]) -> List[Dict[str, Any]]:
    html = fetch_html(source["url"])
    table = read_first_table(html)
    columns = list(table.columns)
    current_column = columns[2] if len(columns) > 2 else None
    previous_column = columns[-1] if len(columns) > 3 else None
    last_three_column = next((col for col in columns if "Last 3" in str(col)), None)
    last_one_column = next((col for col in columns if "Last 1" in str(col)), None)
    home_column = next((col for col in columns if str(col).strip() == "Home"), None)
    away_column = next((col for col in columns if str(col).strip() == "Away"), None)

    items = []
    for row in table.to_dict("records"):
        row_values = {normalize_column_name(key): clean_value(value) for key, value in row.items()}
        items.append(
            {
                "rank": clean_value(row.get("Rank")),
                "team": clean_value(row.get("Team")),
                "metric_key": source["metric_key"],
                "metric_label": source["metric_label"],
                "current_season_label": str(current_column) if current_column else None,
                "current_value": clean_value(row.get(current_column)) if current_column else None,
                "last_3": clean_value(row.get(last_three_column)) if last_three_column else None,
                "last_1": clean_value(row.get(last_one_column)) if last_one_column else None,
                "home": clean_value(row.get(home_column)) if home_column else None,
                "away": clean_value(row.get(away_column)) if away_column else None,
                "previous_season_label": str(previous_column) if previous_column else None,
                "previous_value": clean_value(row.get(previous_column)) if previous_column else None,
                "raw_values": row_values,
                "source_url": source["url"],
            }
        )
    return items


def parse_player_metric(source: Dict[str, str]) -> List[Dict[str, Any]]:
    html = fetch_html(source["url"])
    table = read_first_table(html)
    items = []
    for row in table.to_dict("records"):
        items.append(
            {
                "rank": clean_value(row.get("Rank")),
                "player": clean_value(row.get("Player")),
                "team": clean_value(row.get("Team")),
                "position": clean_value(row.get("Pos")),
                "value": clean_value(row.get("Value")),
                "metric_key": source["metric_key"],
                "metric_label": source["metric_label"],
                "source_url": source["url"],
            }
        )
    return items


def parse_injuries() -> List[Dict[str, Any]]:
    html = fetch_html(INJURIES_URL)
    soup = BeautifulSoup(html, "lxml")
    items = []
    for section in soup.select(".ResponsiveTable.Table__league-injuries"):
        team_node = section.select_one(".injuries__teamName")
        table_node = section.find("table")
        if not team_node or not table_node:
            continue
        team = team_node.get_text(" ", strip=True)
        table = pd.read_html(StringIO(str(table_node)))[0].fillna("")
        for row in table.to_dict("records"):
            items.append(
                {
                    "team": team,
                    "player_name": clean_value(row.get("NOMBRE")),
                    "position": clean_value(row.get("POS")),
                    "estimated_return": clean_value(row.get("FECHA DE REGRESO EST.")),
                    "status": clean_value(row.get("ESTADO")),
                    "source_url": INJURIES_URL,
                }
            )
    return items


def parse_lineups() -> Dict[str, Any]:
    session = create_session()
    session.headers.update({"Referer": "https://www.nba.com/players/todays-lineups"})
    selected_date = None
    payload = None
    for offset in range(0, 4):
        date_key = (datetime.now(timezone.utc) - timedelta(days=offset)).strftime("%Y%m%d")
        response = session.get(LINEUPS_URL_TEMPLATE.format(date_key=date_key), timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            json_payload = response.json()
            if json_payload.get("games"):
                selected_date = date_key
                payload = json_payload
                break
    if not payload:
        return {"lineup_date": None, "items": []}

    items = []
    for game in payload.get("games", []):
        away_team = game.get("awayTeam", {})
        home_team = game.get("homeTeam", {})
        matchup = f"{away_team.get('teamAbbreviation', '')} vs {home_team.get('teamAbbreviation', '')}".strip()
        for side, team_data, opponent_data in [
            ("away", away_team, home_team),
            ("home", home_team, away_team),
        ]:
            for player in team_data.get("players", []):
                items.append(
                    {
                        "lineup_date": selected_date,
                        "game_id": game.get("gameId"),
                        "matchup": matchup,
                        "side": side,
                        "team_id": team_data.get("teamId"),
                        "team_abbreviation": team_data.get("teamAbbreviation"),
                        "opponent_abbreviation": opponent_data.get("teamAbbreviation"),
                        "game_status": game.get("gameStatus"),
                        "game_status_text": game.get("gameStatusText"),
                        "player_name": player.get("playerName"),
                        "position": player.get("position") or "Bench/Inactive",
                        "lineup_status": player.get("lineupStatus"),
                        "roster_status": player.get("rosterStatus"),
                        "is_starter": bool(player.get("position")),
                        "timestamp": player.get("timestamp"),
                        "source_url": LINEUPS_URL_TEMPLATE.format(date_key=selected_date),
                    }
                )
    return {"lineup_date": selected_date, "items": items}


def parse_ats_team(source: Dict[str, str]) -> List[Dict[str, Any]]:
    html = fetch_html(source["url"])
    table = read_first_table(html)
    line_column = next((col for col in table.columns if "Line" in str(col)), None)
    items = []
    for row in table.to_dict("records"):
        diff_value = clean_value(row.get("Diff"))
        covered_value = None
        if diff_value is not None:
            try:
                covered_value = float(diff_value) >= 0
            except (TypeError, ValueError):
                covered_value = None
        items.append(
            {
                "team": source["team"],
                "date": clean_value(row.get("Date")),
                "venue": clean_value(row.get("H/A/N")),
                "opponent": clean_value(row.get("Opponent")),
                "opponent_rank": clean_value(row.get("Opp Rank")),
                "line": clean_value(row.get(line_column)) if line_column else None,
                "result": clean_value(row.get("Result")),
                "diff": diff_value,
                "covered": covered_value,
                "source_url": source["url"],
            }
        )
    return items


def collect_future_items(futures: List[Any], label: str) -> List[Dict[str, Any]]:
    items = []
    for future in futures:
        try:
            items.extend(future.result())
        except Exception as exc:
            logger.warning("Fallo parcial cargando %s: %s", label, exc)
    return items


def build_dataset(dataset_key: str, items: List[Dict[str, Any]], extra_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "dataset_key": dataset_key,
        "label": DATASET_LABELS[dataset_key],
        "updated_at": utc_now_iso(),
        "item_count": len(items),
        "items": items,
        "meta": extra_meta or {},
    }


def write_refresh_log(status: str, trigger: str, summary: Dict[str, Any], error_message: Optional[str] = None) -> None:
    logs_collection.insert_one(
        {
            "status": status,
            "trigger": trigger,
            "summary": summary,
            "error_message": error_message,
            "created_at": utc_now_iso(),
        }
    )


def refresh_all_datasets(trigger: str = "manual") -> Dict[str, Any]:
    if not refresh_lock.acquire(blocking=False):
        return {"status": "busy", "message": "Ya hay una actualización en progreso."}

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            team_futures = [executor.submit(parse_team_metric, source) for source in TEAM_STAT_SOURCES]
            player_futures = [executor.submit(parse_player_metric, source) for source in PLAYER_STAT_SOURCES]
            ats_futures = [executor.submit(parse_ats_team, source) for source in ATS_SOURCES]

            team_items = collect_future_items(team_futures, "team stats")
            player_items = collect_future_items(player_futures, "player stats")
            ats_items = collect_future_items(ats_futures, "ATS")

        injuries_items = parse_injuries()
        lineup_payload = parse_lineups()
        lineups_items = lineup_payload["items"]

        dataset_docs = [
            build_dataset("teams", team_items),
            build_dataset("players", player_items),
            build_dataset("injuries", injuries_items),
            build_dataset("lineups", lineups_items, {"lineup_date": lineup_payload["lineup_date"]}),
            build_dataset("ats", ats_items),
        ]

        for document in dataset_docs:
            datasets_collection.replace_one(
                {"dataset_key": document["dataset_key"]},
                document,
                upsert=True,
            )

        summary = {doc["dataset_key"]: doc["item_count"] for doc in dataset_docs}
        write_refresh_log("success", trigger, summary)
        logger.info("Actualización completada: %s", summary)
        return {
            "status": "success",
            "message": "Datos actualizados correctamente.",
            "summary": summary,
            "updated_at": utc_now_iso(),
        }
    except Exception as exc:
        logger.exception("Error actualizando datasets")
        write_refresh_log("error", trigger, {}, str(exc))
        return {
            "status": "error",
            "message": "No se pudieron actualizar los datos.",
            "error": str(exc),
        }
    finally:
        refresh_lock.release()


def get_last_refresh_at() -> Optional[str]:
    latest = datasets_collection.find_one({}, {"_id": 0, "updated_at": 1}, sort=[("updated_at", -1)])
    return latest.get("updated_at") if latest else None


def has_cached_data() -> bool:
    return datasets_collection.count_documents({}) > 0


def fetch_datasets(category: str) -> List[Dict[str, Any]]:
    if category == "all":
        docs = list(datasets_collection.find({}, {"_id": 0}))
        return sorted(docs, key=lambda value: value.get("dataset_key", ""))
    document = datasets_collection.find_one({"dataset_key": category}, {"_id": 0})
    return [document] if document else []


def matches_filter(value: Optional[str], search: Optional[str]) -> bool:
    if not search:
        return True
    if value is None:
        return False
    return search.lower() in str(value).lower()


def filter_items(dataset_key: str, items: List[Dict[str, Any]], query: Dict[str, Any]) -> List[Dict[str, Any]]:
    filtered = items
    if query.get("search"):
        search = query["search"]
        search_fields = {
            "teams": ["team", "metric_label", "metric_key"],
            "players": ["player", "team", "metric_label"],
            "injuries": ["team", "player_name", "status"],
            "lineups": ["matchup", "team_abbreviation", "player_name", "roster_status"],
            "ats": ["team", "opponent", "result"],
        }[dataset_key]
        filtered = [
            item
            for item in filtered
            if any(matches_filter(item.get(field), search) for field in search_fields)
        ]

    if query.get("team"):
        team = query["team"]
        team_fields = {
            "teams": ["team"],
            "players": ["team"],
            "injuries": ["team"],
            "lineups": ["team_abbreviation", "opponent_abbreviation", "matchup"],
            "ats": ["team", "opponent"],
        }[dataset_key]
        filtered = [
            item
            for item in filtered
            if any(matches_filter(item.get(field), team) for field in team_fields)
        ]

    if query.get("player") and dataset_key in {"players", "injuries", "lineups"}:
        player_field = {"players": "player", "injuries": "player_name", "lineups": "player_name"}[dataset_key]
        filtered = [item for item in filtered if matches_filter(item.get(player_field), query["player"])]

    if query.get("metric") and dataset_key in {"teams", "players"}:
        filtered = [
            item
            for item in filtered
            if matches_filter(item.get("metric_key"), query["metric"])
            or matches_filter(item.get("metric_label"), query["metric"])
        ]

    if query.get("status") and dataset_key in {"injuries", "lineups"}:
        status_fields = {"injuries": ["status"], "lineups": ["lineup_status", "roster_status", "game_status_text"]}[dataset_key]
        filtered = [
            item
            for item in filtered
            if any(matches_filter(item.get(field), query["status"]) for field in status_fields)
        ]

    return filtered[: query.get("limit", 250)]


def query_cached_data(query: Dict[str, Any]) -> Dict[str, Any]:
    raw_docs = fetch_datasets(query.get("category", "all"))
    datasets = []
    for doc in raw_docs:
        if not doc:
            continue
        filtered_items = filter_items(doc["dataset_key"], doc.get("items", []), query)
        datasets.append(
            {
                "dataset_key": doc["dataset_key"],
                "label": doc["label"],
                "updated_at": doc.get("updated_at"),
                "item_count": doc.get("item_count", 0),
                "filtered_count": len(filtered_items),
                "items": filtered_items,
                "meta": doc.get("meta", {}),
            }
        )

    return {
        "category": query.get("category", "all"),
        "filters": {
            key: value
            for key, value in query.items()
            if key in {"search", "team", "player", "metric", "status", "limit"} and value not in [None, ""]
        },
        "last_refresh_at": get_last_refresh_at(),
        "datasets": datasets,
    }