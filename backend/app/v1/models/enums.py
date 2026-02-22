"""Database enums for API v1."""

from enum import StrEnum


class UserPlan(StrEnum):
    """Commercial plan tiers for workspace limits."""

    FREE = "FREE"
    PAID = "PAID"
