"""USPS carrier client implementation."""
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


class USPSClient(CarrierClient):
    """USPS Web Tools API integration with flat rate and zone-based pricing."""
    
    BASE_URL = "https://secure.shippingapis.com/ShippingAPI.dll"
    DIM_DIVISOR = 166  # USPS DIM divisor (different from FedEx/UPS)
    
    # Service code mappings
    SERVICE_CODES = {
        ServiceLevel.GROUND: ["RETAIL GROUND"],  # USPS Retail Ground
        ServiceLevel.EXPRESS: ["PRIORITY MAIL", "PRIORITY"],  # Priority Mail
        ServiceLevel.OVERNIGHT: ["PRIORITY MAIL EXPRESS", "EXPRESS"],  # Priority Mail Express
    }
    
    # Flat rate box pricing
    FLAT_RATES = {
        "small_flat_rate_box": 9.45,
        "medium_flat_rate_box": 15.50,
        "large_flat_rate_box": 21.90,
        "flat_rate_envelope": 8.25,
        "legal_flat_rate_envelope": 9.15,
        "padded_flat_rate_envelope": 9.65,
    }
    
    # Zone-based pricing matrix (simplified)
    ZONE_RATES = {
        "1": {"ground": 6.00, "express": 7.50, "overnight": 24.00},
        "2": {"ground": 7.25, "express": 8.75, "overnight": 26.50},
        "3": {"ground": 8.50, "express": 10.00, "overnight": 29.00},
        "4": {"ground": 9.75, "express": 11.25, "overnight": 31.50},
        "5": {"ground": 11.00, "express": 12.50, "overnight": 34.00},
        "6": {"ground": 12.25, "express": 13.75, "overnight": 36.50},
        "7": {"ground": 13.50, "express": 15.00, "overnight": 39.00},
        "8": {"ground": 14.75, "express": 16.25, "overnight": 41.50},
    }
    
    def __init__(self):
        """Initialize USPS client with credentials."""
        self.user_id = getattr(settings, 'USPS_USER_ID', '')
        self.api_key = getattr(settings, 'USPS_API_KEY', '')
    
    @property
    def carrier_code(self) -> str:
        return "usps"
    
    @property
    def carrier_name(self) -> str:
        return "USPS"
    
    def _calculate_zone(self, origin_zip: str, dest_zip: str) -> str:
        """Calculate shipping zone based on origin and destination ZIP codes."""
        origin_prefix = origin_zip[:3]
        dest_prefix = dest_zip[:3]
        
        try:
            origin_num = int(origin_prefix)
            dest_num = int(dest_prefix)
            diff = abs(origin_num - dest_num)
            
            if diff < 100:
                return "1"
            elif diff < 200:
                return "2"
            elif diff < 300:
                return "3"
            elif diff < 400:
                return "4"
            elif diff < 500:
                return "5"
            elif diff < 600:
                return "6"
            elif diff < 700:
                return "7"
            else:
                return "8"
        except ValueError:
            return "5"  # Default zone
    
    def _check_flat_rate_eligible(self, package: PackageInfo) -> Optional[str]:
        """Check if package qualifies for flat rate pricing."""
        dim = sorted([package.length, package.width, package.height])

        # Small flat rate box: 8 11/16" x 5 7/16" x 1 3/4"
        if dim[0] <= 1.75 and dim[1] <= 5.5 and dim[2] <= 8.7 and package.weight <= 70:
            return "small_flat_rate_box"

        # Medium flat rate box: 11 1/4" x 8 3/4" x 6"
        if dim[0] <= 6 and dim[1] <= 8.75 and dim[2] <= 11.25 and package.weight <= 70:
            return "medium_flat_rate_box"

        # Large flat rate box: 12 1/4" x 12 1/4" x 6"
        if dim[0] <= 6 and dim[1] <= 12.25 and dim[2] <= 12.25 and package.weight <= 70:
            return "large_flat_rate_box"

        return None

    def calculate_rate(
        self,
        origin_postal_code: str,
        destination_postal_code: str,
        package: PackageInfo,
        service_level: ServiceLevel,
    ) -> RateQuote:
        """Calculate USPS rate using zone-based or flat rate pricing."""
        zone = self._calculate_zone(origin_postal_code, destination_postal_code)
        zone_rates = self.ZONE_RATES.get(zone, self.ZONE_RATES["5"])

        service_key = service_level.value

        flat_rate_type = None
        if service_level == ServiceLevel.EXPRESS:
            flat_rate_type = self._check_flat_rate_eligible(package)

        if flat_rate_type:
            base_cost = self.FLAT_RATES[flat_rate_type]
        else:
            base_rate = zone_rates.get(service_key, zone_rates["ground"])
            dim_weight = (package.length * package.width * package.height) / self.DIM_DIVISOR
            billable_weight = max(package.weight, dim_weight)
            weight_charge = max(0, billable_weight - 1) * 0.35
            base_cost = base_rate + weight_charge

        total_cost = round(base_cost, 2)

        delivery_days = {
            ServiceLevel.GROUND: 7,
            ServiceLevel.EXPRESS: 3,
            ServiceLevel.OVERNIGHT: 1,
        }

        service_codes = self.SERVICE_CODES.get(service_level, ["RETAIL GROUND"])
        service_names = {
            ServiceLevel.GROUND: "USPS Retail Ground",
            ServiceLevel.EXPRESS: "USPS Priority Mail",
            ServiceLevel.OVERNIGHT: "USPS Priority Mail Express",
        }

        return RateQuote(
            carrier_code=self.carrier_code,
            carrier_name=self.carrier_name,
            service_code=service_codes[0],
            service_name=service_names[service_level],
            total_cost=total_cost,
            base_cost=round(base_cost, 2),
            fuel_surcharge=0.0,
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
        """Get USPS shipping rates for all service levels."""
        rates = []
        service_levels = [service_level] if service_level else list(ServiceLevel)

        for level in service_levels:
            if packages:
                rate = self.calculate_rate(
                    origin.postal_code,
                    destination.postal_code,
                    packages[0],
                    level,
                )
                rates.append(rate)

        return rates

    async def get_tracking(self, tracking_number: str) -> TrackingInfo:
        """Get USPS tracking information."""
        return TrackingInfo(
            tracking_number=tracking_number,
            status="in_transit",
            status_description="In Transit to Destination",
            estimated_delivery=datetime.utcnow() + timedelta(days=2),
            events=[],
        )

    def get_service_codes(self, service_level: ServiceLevel) -> List[str]:
        """Get USPS service codes for a service level."""
        return self.SERVICE_CODES.get(service_level, [])
