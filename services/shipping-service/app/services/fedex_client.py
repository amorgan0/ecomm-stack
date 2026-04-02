"""FedEx carrier client implementation."""
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


class FedExClient(CarrierClient):
    """FedEx carrier integration with OAuth and zone-based pricing."""
    
    BASE_URL = "https://apis.fedex.com"
    DIM_DIVISOR = 139
    
    SERVICE_CODES = {
        ServiceLevel.GROUND: ["FEDEX_GROUND", "FEDEX_HOME_DELIVERY"],
        ServiceLevel.EXPRESS: ["FEDEX_EXPRESS_SAVER", "FEDEX_2DAY"],
        ServiceLevel.OVERNIGHT: ["FEDEX_PRIORITY_OVERNIGHT", "FEDEX_FIRST_OVERNIGHT"],
    }
    
    ZONE_RATES = {
        "1": {"ground": 8.50, "express": 18.00, "overnight": 42.00},
        "2": {"ground": 9.75, "express": 20.50, "overnight": 45.00},
        "3": {"ground": 11.00, "express": 23.00, "overnight": 48.00},
        "4": {"ground": 12.50, "express": 26.00, "overnight": 52.00},
        "5": {"ground": 14.00, "express": 29.00, "overnight": 56.00},
        "6": {"ground": 15.50, "express": 32.00, "overnight": 60.00},
        "7": {"ground": 17.00, "express": 35.00, "overnight": 64.00},
        "8": {"ground": 18.50, "express": 38.00, "overnight": 68.00},
    }
    
    def __init__(self):
        self.api_key = getattr(settings, 'FEDEX_API_KEY', '')
        self.api_secret = getattr(settings, 'FEDEX_API_SECRET', '')
        self.account_number = getattr(settings, 'FEDEX_ACCOUNT_NUMBER', '')
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
    
    @property
    def carrier_code(self) -> str:
        return "fedex"
    
    @property
    def carrier_name(self) -> str:
        return "FedEx"
    
    def _calculate_zone(self, origin_zip: str, dest_zip: str) -> str:
        origin_prefix = origin_zip[:3]
        dest_prefix = dest_zip[:3]
        
        try:
            origin_num = int(origin_prefix)
            dest_num = int(dest_prefix)
            diff = abs(origin_num - dest_num)
            
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
        return round(base_cost * 0.12, 2)  # 12% fuel surcharge
    
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
        weight_charge = max(0, billable_weight - 5) * 0.45
        base_cost = base_rate + weight_charge
        fuel_surcharge = self._calculate_fuel_surcharge(base_cost)
        total_cost = round(base_cost + fuel_surcharge, 2)
        
        delivery_days = {ServiceLevel.GROUND: 5, ServiceLevel.EXPRESS: 3, ServiceLevel.OVERNIGHT: 1}
        service_names = {
            ServiceLevel.GROUND: "FedEx Ground",
            ServiceLevel.EXPRESS: "FedEx Express Saver",
            ServiceLevel.OVERNIGHT: "FedEx Priority Overnight",
        }
        
        return RateQuote(
            carrier_code=self.carrier_code,
            carrier_name=self.carrier_name,
            service_code=self.SERVICE_CODES.get(service_level, ["FEDEX_GROUND"])[0],
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
