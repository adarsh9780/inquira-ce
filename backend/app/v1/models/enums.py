"""Database enums for API v1."""

from enum import StrEnum


class UserPlan(StrEnum):
    """Commercial plan tiers attached to a user record."""

    FREE = "FREE"
    PAID = "PAID"
