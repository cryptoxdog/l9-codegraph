"""
Transaction domain model.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Any, Optional


@dataclass
class TransactionAttribution:
    gclid: Optional[str] = None
    gbraid: Optional[str] = None
    wbraid: Optional[str] = None
    conversion_action_id: Optional[str] = None
    conversion_value: Optional[float] = None
    conversion_reported: bool = False
    conversion_reported_at: Optional[datetime] = None
    conversion_match_type: Optional[str] = None

    @property
    def has_click_id(self) -> bool:
        return bool(self.gclid or self.gbraid or self.wbraid)


@dataclass
class Transaction:
    transaction_id: Optional[str] = None
    contact_id: Optional[str] = None
    account_id: Optional[str] = None
    location_id: Optional[str] = None
    transaction_date: Optional[date] = None
    transaction_time: Optional[time] = None
    ticket_number: Optional[str] = None
    transaction_type: str = "purchase"
    material_type: Optional[str] = None
    material_grade: Optional[str] = None
    weight_pounds: Optional[float] = None
    weight_kg: Optional[float] = None
    unit_price: Optional[float] = None
    line_items: list[dict[str, Any]] = field(default_factory=list)
    subtotal: Optional[float] = None
    tax_amount: float = 0.0
    total_amount: float = 0.0
    currency_code: str = "USD"
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    payment_status: str = "pending"
    payment_date: Optional[date] = None
    payment_reference: Optional[str] = None
    attribution: TransactionAttribution = field(default_factory=TransactionAttribution)
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    scale_id: Optional[str] = None
    cashier_user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def needs_conversion_export(self) -> bool:
        return (
            not self.attribution.conversion_reported
            and self.total_amount > 0
            and (self.contact_id is not None or self.account_id is not None)
        )

    @property
    def conversion_datetime(self) -> Optional[datetime]:
        if self.transaction_date and self.transaction_time:
            return datetime.combine(self.transaction_date, self.transaction_time)
        return self.created_at
