"""HTTP routes for the recommendation service."""

from fastapi import APIRouter, HTTPException, Path, Query

from .schemas import HealthResponse, RecommendationListResponse, UserStatsResponse
from .services import (
    fetch_user_stats,
    get_collaborative_recommendations,
    get_health_status,
    get_regional_recommendations,
    get_similar_recommendations,
    get_trending_recommendations,
)

router = APIRouter()


def _handle_service_exception(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=503, detail="Neo4j service unavailable") from exc


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    try:
        return HealthResponse(**get_health_status())
    except Exception as exc:  # pragma: no cover - exercised by API tests
        _handle_service_exception(exc)


@router.get("/users/{user_id}/recommendations/similar", response_model=RecommendationListResponse)
def similar_recommendations(
    user_id: str = Path(..., min_length=1),
    limit: int = Query(5, ge=1, le=10),
) -> RecommendationListResponse:
    try:
        recommendations = get_similar_recommendations(user_id, limit)
        return RecommendationListResponse(user_id=user_id, limit=limit, recommendations=recommendations)
    except Exception as exc:  # pragma: no cover - exercised by API tests
        _handle_service_exception(exc)


@router.get("/users/{user_id}/recommendations/collaborative", response_model=RecommendationListResponse)
def collaborative_recommendation_list(
    user_id: str = Path(..., min_length=1),
    limit: int = Query(5, ge=1, le=10),
) -> RecommendationListResponse:
    try:
        recommendations = get_collaborative_recommendations(user_id, limit)
        return RecommendationListResponse(user_id=user_id, limit=limit, recommendations=recommendations)
    except Exception as exc:  # pragma: no cover - exercised by API tests
        _handle_service_exception(exc)


@router.get("/users/{user_id}/recommendations/regional", response_model=RecommendationListResponse)
def regional_recommendation_list(
    user_id: str = Path(..., min_length=1),
    limit: int = Query(5, ge=1, le=10),
) -> RecommendationListResponse:
    try:
        recommendations = get_regional_recommendations(user_id, limit)
        return RecommendationListResponse(user_id=user_id, limit=limit, recommendations=recommendations)
    except Exception as exc:  # pragma: no cover - exercised by API tests
        _handle_service_exception(exc)


@router.get("/users/{user_id}/recommendations/trending", response_model=RecommendationListResponse)
def trending_recommendation_list(
    user_id: str = Path(..., min_length=1),
    limit: int = Query(5, ge=1, le=10),
) -> RecommendationListResponse:
    try:
        recommendations = get_trending_recommendations(user_id, limit)
        return RecommendationListResponse(user_id=user_id, limit=limit, recommendations=recommendations)
    except Exception as exc:  # pragma: no cover - exercised by API tests
        _handle_service_exception(exc)


@router.get("/users/{user_id}/stats", response_model=UserStatsResponse)
def user_stats(user_id: str = Path(..., min_length=1)) -> UserStatsResponse:
    try:
        stats = fetch_user_stats(user_id)
        if stats is None:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        return UserStatsResponse(**stats)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - exercised by API tests
        _handle_service_exception(exc)
