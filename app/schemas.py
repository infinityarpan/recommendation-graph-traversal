"""Pydantic models for the recommendation API."""

from typing import List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class PackageRecommendation(BaseModel):
    id: str
    name: str
    price: int
    category: str
    similarity_score: Optional[int] = None
    popularity_score: Optional[int] = None
    engagement_score: Optional[int] = None
    user_count: Optional[int] = None
    city: Optional[str] = None
    region: Optional[str] = None


class RecommendationListResponse(BaseModel):
    user_id: str
    limit: int
    recommendations: List[PackageRecommendation]


class UserStatsResponse(BaseModel):
    user_id: str
    total_actions: int
    views: int
    clicks: int
    added_to_cart: int
    bookings: int
    abandoned: int
    unique_packages: int
