"""Base carrier client interface for shipping service."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ServiceLevel(str, Enum):
    """Service level types for shipping."""
    GROUND = "ground"
    EXPRESS = "express"
    OVERNIGHT = "overnight"


@dataclass
class PackageInfo:
    """Package information for rate calculation."""
    weight: float  # Weight in pounds
    length: float  # Length in inches
    width: float   # Width in inches
    height: float  # Height in inches
    value: Optional[float] = None  # Declared value for insurance
    
    @property
    def dimensional_weight(self) -> float:
        """Calculate dimensional weight (DIM weight) in pounds."""
        return (self.length * self.width * self.height) / 139
    
    @property
    def billable_weight(self) -> float:
        """Return the greater of actual weight and dimensional weight."""
        return max(self.weight, self.dimensional_weight)


@dataclass
class RateQuote:
    """Rate quote from carrier."""
    carrier_code: str
    carrier_name: str
    service_code: str
    service_name: str
    total_cost: float
    base_cost: float
    fuel_surcharge: float = 0.0
    estimated_delivery_days: int = 5
    estimated_delivery_date: Optional[datetime] = None
    guaranteed_delivery: bool = False
    currency: str = "USD"


@dataclass
class AddressInfo:
    """Address information for shipping."""
    name: str
    address1: str
    city: str
    state: str
    postal_code: str
    country: str = "US"
    address2: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class TrackingInfo:
    """Tracking information from carrier."""
    tracking_number: str
    status: str
    status_description: str
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    events: List[Dict[str, Any]] = None
    signed_by: Optional[str] = None
    
    def __post_init__(self):
        if self.events is None:
            self.events = []


class CarrierClient(ABC):
    """Abstract base class for carrier integrations."""
    
    @property
    @abstractmethod
    def carrier_code(self) -> str:
        """Carrier code identifier."""
        pass
    
    @property
    @abstractmethod
    def carrier_name(self) -> str:
        """Human-readable carrier name."""
        pass
    
    @abstractmethod
    async def get_rates(
        self,
        origin: AddressInfo,
        destination: AddressInfo,
        packages: List[PackageInfo],
        service_level: Optional[ServiceLevel] = None,
    ) -> List[RateQuote]:
        """Get shipping rates for packages."""
        pass
    
    @abstractmethod
    async def get_tracking(self, tracking_number: str) -> TrackingInfo:
        """Get tracking information."""
        pass
    
    @abstractmethod
    def calculate_rate(
        self,
        origin_postal_code: str,
        destination_postal_code: str,
        package: PackageInfo,
        service_level: ServiceLevel,
    ) -> RateQuote:
        """Calculate rate using carrier-specific pricing rules."""
        pass
    
    @abstractmethod
    def get_service_codes(self, service_level: ServiceLevel) -> List[str]:
        """Get carrier-specific service codes for a service level."""
        pass
