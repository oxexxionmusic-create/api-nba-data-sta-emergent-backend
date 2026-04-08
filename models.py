from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class DataQuery(BaseModel):
    category: Literal["all", "teams", "players", "injuries", "lineups", "ats"] = "all"
    search: Optional[str] = None
    team: Optional[str] = None
    player: Optional[str] = None
    metric: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(default=250, ge=1, le=5000)
    api_key: Optional[str] = None


class FunctionRequest(DataQuery):
    action: Literal["query", "refresh"] = "query"
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None


class DatasetResponse(BaseModel):
    dataset_key: str
    label: str
    updated_at: Optional[str] = None
    item_count: int
    filtered_count: int
    items: List[Dict[str, Any]]


class PublicInfoResponse(BaseModel):
    service: str
    api_key: str
    docs_url: str
    available_categories: List[str]
    auto_refresh: str
    last_refresh_at: Optional[str] = None
    usage_examples: Dict[str, Any]