"""Core public API regression tests for docs, query, and admin refresh flows."""

import os
from pathlib import Path

import requests
from dotenv import dotenv_values


def _get_base_url() -> str:
    env_url = os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")

    frontend_env = Path(__file__).resolve().parents[2] / "frontend" / ".env"
    values = dotenv_values(frontend_env)
    file_url = values.get("REACT_APP_BACKEND_URL")
    if not file_url:
        raise RuntimeError("Missing REACT_APP_BACKEND_URL for API tests")
    return str(file_url).rstrip("/")


BASE_URL = _get_base_url()
API_KEY = "SPORTOX-NBA-GLOBAL-2026"
ADMIN_EMAIL = "edrianttrejol@gmail.com"
ADMIN_PASSWORD = "sportox@22NBA"


def test_public_info_exposes_global_key_and_usage_examples():
    response = requests.get(f"{BASE_URL}/api/public-info", timeout=30)
    assert response.status_code == 200

    data = response.json()
    assert data["api_key"] == API_KEY
    assert "usage_examples" in data and "post_funcion_query" in data["usage_examples"]


def test_get_datos_requires_api_key():
    response = requests.get(f"{BASE_URL}/api/datos?category=teams&limit=1", timeout=30)
    assert response.status_code == 401

    data = response.json()
    assert data["detail"] == "API Key inválida."


def test_get_datos_with_api_key_returns_cached_json():
    response = requests.get(
        f"{BASE_URL}/api/datos?category=teams&limit=5",
        headers={"x-api-key": API_KEY},
        timeout=45,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["category"] == "teams"
    assert isinstance(data.get("datasets"), list)
    assert len(data["datasets"]) == 1
    dataset = data["datasets"][0]
    assert dataset["dataset_key"] == "teams"
    assert isinstance(dataset["items"], list)


def test_post_funcion_query_returns_players_filtered_dataset():
    response = requests.post(
        f"{BASE_URL}/api/funcion",
        json={
            "action": "query",
            "category": "players",
            "metric": "points",
            "limit": 5,
            "api_key": API_KEY,
        },
        headers={"x-api-key": API_KEY},
        timeout=45,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["category"] == "players"
    assert len(data["datasets"]) == 1
    assert data["datasets"][0]["dataset_key"] == "players"


def test_post_funcion_refresh_rejects_bad_admin_credentials():
    response = requests.post(
        f"{BASE_URL}/api/funcion",
        json={
            "action": "refresh",
            "api_key": API_KEY,
            "admin_email": "bad@example.com",
            "admin_password": "badpass",
        },
        headers={"x-api-key": API_KEY},
        timeout=30,
    )
    assert response.status_code == 403

    data = response.json()
    assert data["detail"] == "Credenciales de administrador inválidas."


def test_post_funcion_refresh_accepts_admin_credentials():
    response = requests.post(
        f"{BASE_URL}/api/funcion",
        json={
            "action": "refresh",
            "api_key": API_KEY,
            "admin_email": ADMIN_EMAIL,
            "admin_password": ADMIN_PASSWORD,
        },
        headers={"x-api-key": API_KEY},
        timeout=120,
    )
    assert response.status_code == 200

    data = response.json()
    assert data.get("status") in {"success", "busy"}
    if data.get("status") == "success":
        assert isinstance(data.get("summary"), dict)
