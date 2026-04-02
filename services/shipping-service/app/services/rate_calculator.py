"""Rate calculation module with carrier-specific pricing and caching."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.services.carrier_base import (
    AddressInfo,
    PackageInfo,
    RateQuote,
    ServiceLevel,
)
from app.services.fedex_client import FedExClient
from app.services.ups_client import UPSClient
from app.services.usps_client import USPSClient

logger = logging.getLogger(__name__)


class RateCalculator:
    """Calculate shipping rates across multiple carriers with caching."""
    
    CACHE_TTL = 300  # 5 minutes
    
    def __init__(self, carriers: Optional[List[str]] = None):
        """Initialize rate calculator with specified carriers."""
        self._carriers = {
            "fedex": FedExClient(),
            "ups": UPSClient(),
            "usps": USPSClient(),
        }
        
        if carriers:
            self._carriers = {
                k: v for k, v in self._carriers.items() if k in carriers
            }
    
    def calculate_rates(
        self,
        origin: AddressInfo,
        destination: AddressInfo,
        packages: List[PackageInfo],
        service_level: Optional[ServiceLevel] = None,
    ) -> Dict[str, List[RateQuote]]:
        """Calculate rates for all carriers."""
        results = {}
        
        for carrier_code, client in self._carriers.items():
            try:
                rates = self._calculate_carrier_rates(
                    client, origin, destination, packages, service_level
                )
                results[carrier_code] = rates
            except Exception as e:
                logger.error(f"Error calculating rates for {carrier_code}: {e}")
                results[carrier_code] = []
        
        return results
    
    def _calculate_carrier_rates(
        self,
        client,
        origin: AddressInfo,
        destination: AddressInfo,
        packages: List[PackageInfo],
        service_level: Optional[ServiceLevel],
    ) -> List[RateQuote]:
        """Calculate rates for a single carrier (sync wrapper for async method)."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    client.get_rates(origin, destination, packages, service_level)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                client.get_rates(origin, destination, packages, service_level)
            )
    
    def get_cheapest_rate(
        self,
        origin: AddressInfo,
        destination: AddressInfo,
        packages: List[PackageInfo],
        service_level: Optional[ServiceLevel] = None,
    ) -> Optional[RateQuote]:
        """Get the cheapest rate across all carriers."""
        all_rates = self.calculate_rates(origin, destination, packages, service_level)
        
        cheapest = None
        for carrier_rates in all_rates.values():
            for rate in carrier_rates:
                if cheapest is None or rate.total_cost < cheapest.total_cost:
                    cheapest = rate
        
        return cheapest
    
    def get_fastest_rate(
        self,
        origin: AddressInfo,
        destination: AddressInfo,
        packages: List[PackageInfo],
    ) -> Optional[RateQuote]:
        """Get the fastest delivery rate across all carriers."""
        all_rates = self.calculate_rates(origin, destination, packages)
        
        fastest = None
        for carrier_rates in all_rates.values():
            for rate in carrier_rates:
                if fastest is None or rate.estimated_delivery_days < fastest.estimated_delivery_days:
                    fastest = rate
        
        return fastest
    
    def get_best_value_rate(
        self,
        origin: AddressInfo,
        destination: AddressInfo,
        packages: List[PackageInfo],
    ) -> Optional[RateQuote]:
        """Get the best value rate (balance of cost and speed)."""
        all_rates = self.calculate_rates(origin, destination, packages)
        
        best = None
        best_score = float('inf')
        
        for carrier_rates in all_rates.values():
            for rate in carrier_rates:
                score = rate.total_cost / (rate.estimated_delivery_days + 1)
                if score < best_score:
                    best_score = score
                    best = rate
        
        return best
