from datetime import datetime, timedelta, timezone
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import APIRouter, FastAPI, Header, HTTPException
from starlette.middleware.cors import CORSMiddleware

from config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    API_GLOBAL_KEY,
    APP_DESCRIPTION,
    APP_TITLE,
    AUTO_REFRESH_HOURS,
    CORS_ORIGINS,
    DATASET_LABELS,
)
from models import FunctionRequest, PublicInfoResponse
from scraper_service import get_last_refresh_at, has_cached_data, query_cached_data, refresh_all_datasets


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")
app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION, version="1.0.0")
api_router = APIRouter(prefix="/api")


def ensure_api_key(header_key: str | None, body_key: str | None = None) -> None:
    provided_key = header_key or body_key
    if provided_key != API_GLOBAL_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida.")


def ensure_admin(email: str | None, password: str | None) -> None:
    if email != ADMIN_EMAIL or password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Credenciales de administrador inválidas.")


def scheduled_refresh() -> None:
    logger.info("Ejecutando actualización programada...")
    refresh_all_datasets(trigger="scheduled")


@api_router.get("/")
def api_root() -> dict:
    return {
        "service": APP_TITLE,
        "status": "online",
        "available_endpoints": ["GET /api/public-info", "GET /api/datos", "POST /api/funcion"],
        "last_refresh_at": get_last_refresh_at(),
    }


@api_router.get("/public-info", response_model=PublicInfoResponse)
def public_info() -> dict:
    return {
        "service": APP_TITLE,
        "api_key": API_GLOBAL_KEY,
        "docs_url": "/docs",
        "available_categories": list(DATASET_LABELS.keys()),
        "auto_refresh": f"Cada {AUTO_REFRESH_HOURS} horas (2 veces al día)",
        "last_refresh_at": get_last_refresh_at(),
        "usage_examples": {
            "get_datos": {
                "method": "GET",
                "url": "/api/datos?category=teams&metric=points_per_game&limit=20",
                "headers": {"x-api-key": API_GLOBAL_KEY},
            },
            "post_funcion_query": {
                "method": "POST",
                "url": "/api/funcion",
                "body": {
                    "action": "query",
                    "category": "players",
                    "metric": "points",
                    "limit": 10,
                    "api_key": API_GLOBAL_KEY,
                },
            },
            "post_funcion_refresh": {
                "method": "POST",
                "url": "/api/funcion",
                "body": {
                    "action": "refresh",
                    "api_key": API_GLOBAL_KEY,
                    "admin_email": "admin@privado",
                    "admin_password": "********",
                },
            },
        },
    }


@api_router.get("/datos")
def get_datos(
    category: str = "all",
    search: str | None = None,
    team: str | None = None,
    player: str | None = None,
    metric: str | None = None,
    status: str | None = None,
    limit: int = 250,
    api_key: str | None = None,
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> dict:
    ensure_api_key(x_api_key, api_key)
    return query_cached_data(
        {
            "category": category,
            "search": search,
            "team": team,
            "player": player,
            "metric": metric,
            "status": status,
            "limit": limit,
        }
    )


@api_router.post("/funcion")
def post_funcion(payload: FunctionRequest, x_api_key: str | None = Header(default=None, alias="x-api-key")) -> dict:
    ensure_api_key(x_api_key, payload.api_key)

    if payload.action == "refresh":
        ensure_admin(payload.admin_email, payload.admin_password)
        return refresh_all_datasets(trigger="manual")

    return query_cached_data(payload.model_dump(exclude={"action", "api_key", "admin_email", "admin_password"}))


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    if not scheduler.running:
        scheduler.add_job(
            scheduled_refresh,
            "interval",
            hours=AUTO_REFRESH_HOURS,
            id="nba-cache-refresh",
            replace_existing=True,
            next_run_time=datetime.now(timezone.utc) + timedelta(hours=AUTO_REFRESH_HOURS),
        )
        scheduler.start()
    if not has_cached_data():
        logger.info("No hay caché inicial; disparando primera carga...")
        refresh_all_datasets(trigger="bootstrap")


@app.on_event("shutdown")
def shutdown_event() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)