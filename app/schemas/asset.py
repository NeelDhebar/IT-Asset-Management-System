"""Pydantic schemas for IT Asset management."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import AssetStatus, AssetType


class AssetBase(BaseModel):
    asset_id: str = Field(..., min_length=3, max_length=50)
    asset_type: AssetType
    brand: str = Field(..., max_length=100)
    model: str = Field(..., max_length=100)
    serial_number: str = Field(..., max_length=100)
    purchase_date: str
    purchase_cost: float = Field(default=0.0, ge=0.0)


class AssetCreate(AssetBase):
    specs: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    purchase_cost: Optional[float] = None
    status: Optional[AssetStatus] = None
    specs: Optional[Dict[str, Any]] = None


class AssetAssignRequest(BaseModel):
    user_id: str
    notes: Optional[str] = None


class BatchAssetReturnRequest(BaseModel):
    asset_ids: list[str] = Field(..., min_length=1)


class AssetResponse(AssetBase):
    id: int
    status: AssetStatus
    assigned_to: Optional[str] = None
    specs_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
