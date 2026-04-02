"""Factory for creating carrier client instances."""
import logging
from typing import Dict, Optional, Type

from app.services.carrier_base import CarrierClient
from app.services.fedex_client import FedExClient
from app.services.ups_client import UPSClient
from app.services.usps_client import USPSClient

logger = logging.getLogger(__name__)


class CarrierClientFactory:
    """Factory for creating and managing carrier client instances."""
    
    # Registry of available carrier clients
    _registry: Dict[str, Type[CarrierClient]] = {
        "fedex": FedExClient,
        "ups": UPSClient,
        "usps": USPSClient,
    }
    
    # Singleton instances
    _instances: Dict[str, CarrierClient] = {}
    
    @classmethod
    def get_client(cls, carrier_code: str) -> CarrierClient:
        """Get carrier client instance by carrier code.
        
        Args:
            carrier_code: Carrier code (e.g., 'fedex', 'ups', 'usps')
            
        Returns:
            CarrierClient instance
            
        Raises:
            ValueError: If carrier code is not registered
        """
        carrier_code = carrier_code.lower()
        
        if carrier_code not in cls._registry:
            raise ValueError(
                f"Unknown carrier code: {carrier_code}. "
                f"Available carriers: {list(cls._registry.keys())}"
            )
        
        # Return cached instance if available
        if carrier_code not in cls._instances:
            client_class = cls._registry[carrier_code]
            cls._instances[carrier_code] = client_class()
            logger.info(f"Created new {carrier_code} client instance")
        
        return cls._instances[carrier_code]
    
    @classmethod
    def get_all_clients(cls) -> Dict[str, CarrierClient]:
        """Get all registered carrier clients.
        
        Returns:
            Dictionary mapping carrier codes to client instances
        """
        return {
            code: cls.get_client(code)
            for code in cls._registry
        }
    
    @classmethod
    def register_carrier(cls, carrier_code: str, client_class: Type[CarrierClient]) -> None:
        """Register a new carrier client class.
        
        Args:
            carrier_code: Unique carrier code
            client_class: CarrierClient subclass
        """
        cls._registry[carrier_code.lower()] = client_class
        logger.info(f"Registered carrier: {carrier_code}")
    
    @classmethod
    def get_available_carriers(cls) -> list:
        """Get list of available carrier codes.
        
        Returns:
            List of carrier codes
        """
        return list(cls._registry.keys())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached client instances."""
        cls._instances.clear()
        logger.info("Cleared carrier client cache")
