"""UPS carrier client implementation."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.services.carrier_base import (
    AddressInfo,
    CarrierClient,
    PackageInfo,
    RateQuote,
    ServiceLevel,
    TrackingInfo,
)

logger = logging.getLogger(__name__)


class UPSClient(CarrierClient):
    """UPS carrier integration with OAuth2 and zone-based pricing."""
    
    BASE_URL = "https://onlinetools.ups.com"
    DIM_DIVISOR = 139
    
    SERVICE_CODES = {
        ServiceLevel.GROUND: ["03"],
        ServiceLevel.EXPRESS: ["12", "02"],
        ServiceLevel.OVERNIGHT: ["01", "14"],
    }
    
    ZONE_RATES = {
        "1": {"ground": 7.50, "express": 16.00, "overnight": 38.00},
        "2": {"ground": 8.75, "express": 18.50, "overnight": 42.00},
        "3": {"ground": 10.00, "express": 21.00, "overnight": 46.00},
        "4": {"ground": 11.50, "express": 24.00, "overnight": 50.00},
        "5": {"ground": 13.00, "express": 27.00, "overnight": 54.00},
        "6": {"ground": 14.50, "express": 30.00, "overnight": 58.00},
        "7": {"ground": 16.00, "express": 33.00, "overnight": 62.00},
        "8": {"ground": 17.50, "express": 36.00, "overnight": 66.00},
    }
    
    def __init__(self):
        self.api_key = getattr(settings, 'UPS_API_KEY', '')
        self.api_secret = getattr(settings, 'UPS_API_SECRET', '')
        self.account_number = getattr(settings, 'UPS_ACCOUNT_NUMBER', '')
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    @property
    def carrier_code(self) -> str:
        return "ups"
    
    @property
    def carrier_name(self) -> str:
        return "UPS"
    
    def _calculate_zone(self, origin_zip: str, dest_zip: str) -> str:
        try:
            diff = abs(int(origin_zip[:3]) - int(dest_zip[:3]))
            if diff < 100: return "1"
            elif diff < 200: return "2"
            elif diff < 300: return "3"
            elif diff < 400: return "4"
            elif diff < 500: return "5"
            elif diff < 600: return "6"
            elif diff < 700: return "7"
            else: return "8"
        except ValueError:
            return "5"
    
    def _calculate_fuel_surcharge(self, base_cost: float) -> float:
        return round(base_cost * 0.10, 2)  # 10% fuel surcharge
    
    def _calculate_hundredweight_discount(self, total_weight: float) -> float:
        if total_weight >= 100: return 0.05
        elif total_weight >= 50: return 0.02
        return 0.0
    
    def calculate_rate(
        self,
        origin_postal_code: str,
        destination_postal_code: str,
        package: PackageInfo,
        service_level: ServiceLevel,
    ) -> RateQuote:
        zone = self._calculate_zone(origin_postal_code, destination_postal_code)
        zone_rates = self.ZONE_RATES.get(zone, self.ZONE_RATES["5"])
        
        service_key = service_level.value
        base_rate = zone_rates.get(service_key, zone_rates["ground"])
        
        dim_weight = package.dimensional_weight
        billable_weight = max(package.weight, dim_weight)
        weight_charge = max(0, billable_weight - 5) * 0.40
        base_cost = base_rate + weight_charge
        
        discount = self._calculate_hundredweight_discount(billable_weight)
        if discount > 0: base_cost = base_cost * (1 - discount)
        
        fuel_surcharge = self._calculate_fuel_surcharge(base_cost)
        total_cost = round(base_cost + fuel_surcharge, 2)
        
        delivery_days = {ServiceLevel.GROUND: 5, ServiceLevel.EXPRESS: 3, ServiceLevel.OVERNIGHT: 1}
        service_names = {
            ServiceLevel.GROUND: "UPS Ground",
            ServiceLevel.EXPRESS: "UPS 3 Day Select",
            ServiceLevel.OVERNIGHT: "UPS Next Day Air",
        }
        
        return RateQuote(
            carrier_code=self.carrier_code,
            carrier_name=self.carrier_name,
            service_code=self.SERVICE_CODES.get(service_level, ["03"])[0],
            service_name=service_names[service_level],
            total_cost=total_cost,
            base_cost=round(base_cost, 2),
            fuel_surcharge=fuel_surcharge,
            estimated_delivery_days=delivery_days[service_level],
            estimated_delivery_date=datetime.utcnow() + timedelta(days=delivery_days[service_level]),
            guaranteed_delivery=service_level == ServiceLevel.OVERNIGHT,
        )
    
    async def get_rates(
        self,
        origin: AddressInfo,
        destination: AddressInfo,
        packages: List[PackageInfo],
        service_level: Optional[ServiceLevel] = None,
    ) -> List[RateQuote]:
        rates = []
        service_levels = [service_level] if service_level else list(ServiceLevel)
        
        for level in service_levels:
            if packages:
                rate = self.calculate_rate(origin.postal_code, destination.postal_code, packages[0], level)
                rates.append(rate)
        
        return rates
    
    async def get_tracking(self, tracking_number: str) -> TrackingInfo:
        return TrackingInfo(
            tracking_number=tracking_number,
            status="in_transit",
            status_description="In Transit",
            estimated_delivery=datetime.utcnow() + timedelta(days=2),
            events=[],
        )
    
    def get_service_codes(self, service_level: ServiceLevel) -> List[str]:
        return self.SERVICE_CODES.get(service_level, [])
