"""Tests for carrier client implementations."""
import pytest
from datetime import datetime, timedelta

from app.services.carrier_base import (
    AddressInfo,
    PackageInfo,
    ServiceLevel,
)
from app.services.fedex_client import FedExClient
from app.services.ups_client import UPSClient
from app.services.usps_client import USPSClient
from app.services.carrier_factory import CarrierClientFactory


class TestFedExClient:
    """Tests for FedEx carrier client."""
    
    @pytest.fixture
    def fedex_client(self):
        """Create FedEx client instance."""
        return FedExClient()
    
    @pytest.fixture
    def sample_package(self):
        """Create sample package."""
        return PackageInfo(weight=5.0, length=12.0, width=8.0, height=6.0)
    
    def test_carrier_code(self, fedex_client):
        """Test carrier code is correct."""
        assert fedex_client.carrier_code == "fedex"
    
    def test_carrier_name(self, fedex_client):
        """Test carrier name is correct."""
        assert fedex_client.carrier_name == "FedEx"
    
    def test_calculate_zone_nearby(self, fedex_client):
        """Test zone calculation for nearby ZIP codes."""
        zone = fedex_client._calculate_zone("90210", "90220")
        assert zone == "1"
    
    def test_calculate_zone_far(self, fedex_client):
        """Test zone calculation for distant ZIP codes."""
        zone = fedex_client._calculate_zone("90210", "10001")
        assert zone in ["7", "8"]
    
    def test_calculate_fuel_surcharge(self, fedex_client):
        """Test fuel surcharge calculation."""
        surcharge = fedex_client._calculate_fuel_surcharge(100.0)
        assert surcharge == 12.0  # 12% of 100
    
    def test_calculate_rate_ground(self, fedex_client, sample_package):
        """Test ground rate calculation."""
        rate = fedex_client.calculate_rate(
            origin_postal_code="90210",
            destination_postal_code="10001",
            package=sample_package,
            service_level=ServiceLevel.GROUND,
        )
        
        assert rate.carrier_code == "fedex"
        assert rate.service_code == "FEDEX_GROUND"
        assert rate.total_cost > 0
        assert rate.fuel_surcharge > 0
        assert rate.estimated_delivery_days == 5
    
    def test_calculate_rate_express(self, fedex_client, sample_package):
        """Test express rate calculation."""
        rate = fedex_client.calculate_rate(
            origin_postal_code="90210",
            destination_postal_code="10001",
            package=sample_package,
            service_level=ServiceLevel.EXPRESS,
        )
        
        assert rate.service_code == "FEDEX_EXPRESS_SAVER"
        assert rate.estimated_delivery_days == 3
    
    def test_calculate_rate_overnight(self, fedex_client, sample_package):
        """Test overnight rate calculation."""
        rate = fedex_client.calculate_rate(
            origin_postal_code="90210",
            destination_postal_code="10001",
            package=sample_package,
            service_level=ServiceLevel.OVERNIGHT,
        )
        
        assert rate.service_code == "FEDEX_PRIORITY_OVERNIGHT"
        assert rate.estimated_delivery_days == 1
        assert rate.guaranteed_delivery is True
    
    @pytest.mark.asyncio
    async def test_get_rates_all_services(self, fedex_client, sample_package):
        """Test getting rates for all service levels."""
        origin = AddressInfo(name="Test", address1="123 Main", city="LA", state="CA", postal_code="90210")
        destination = AddressInfo(name="Test", address1="456 Oak", city="NYC", state="NY", postal_code="10001")
        
        rates = await fedex_client.get_rates(
            origin=origin,
            destination=destination,
            packages=[sample_package],
        )
        
        assert len(rates) == 3  # Ground, Express, Overnight
    
    @pytest.mark.asyncio
    async def test_get_tracking(self, fedex_client):
        """Test tracking info retrieval."""
        tracking = await fedex_client.get_tracking("123456789012")
        
        assert tracking.tracking_number == "123456789012"
        assert tracking.status == "in_transit"


class TestUPSClient:
    """Tests for UPS carrier client."""
    
    @pytest.fixture
    def ups_client(self):
        """Create UPS client instance."""
        return UPSClient()
    
    @pytest.fixture
    def sample_package(self):
        """Create sample package."""
        return PackageInfo(weight=5.0, length=12.0, width=8.0, height=6.0)
    
    def test_carrier_code(self, ups_client):
        """Test carrier code is correct."""
        assert ups_client.carrier_code == "ups"
    
    def test_carrier_name(self, ups_client):
        """Test carrier name is correct."""
        assert ups_client.carrier_name == "UPS"
    
    def test_calculate_rate_ground(self, ups_client, sample_package):
        """Test ground rate calculation."""
        rate = ups_client.calculate_rate(
            origin_postal_code="90210",
            destination_postal_code="10001",
            package=sample_package,
            service_level=ServiceLevel.GROUND,
        )
        
        assert rate.carrier_code == "ups"
        assert rate.service_code == "03"  # UPS Ground code
        assert rate.total_cost > 0
    
    def test_calculate_rate_overnight(self, ups_client, sample_package):
        """Test overnight rate calculation."""
        rate = ups_client.calculate_rate(
            origin_postal_code="90210",
            destination_postal_code="10001",
            package=sample_package,
            service_level=ServiceLevel.OVERNIGHT,
        )
        
        assert rate.service_code == "01"  # UPS Next Day Air
        assert rate.guaranteed_delivery is True
    
    def test_hundredweight_discount(self, ups_client):
        """Test hundredweight discount for heavy packages."""
        heavy_package = PackageInfo(weight=120.0, length=12.0, width=8.0, height=6.0)
        
        rate = ups_client.calculate_rate(
            origin_postal_code="90210",
            destination_postal_code="10001",
            package=heavy_package,
            service_level=ServiceLevel.GROUND,
        )
        
        assert rate.total_cost > 0


class TestUSPSClient:
    """Tests for USPS carrier client."""
    
    @pytest.fixture
    def usps_client(self):
        """Create USPS client instance."""
        return USPSClient()
    
    def test_carrier_code(self, usps_client):
        """Test carrier code is correct."""
        assert usps_client.carrier_code == "usps"
    
    def test_carrier_name(self, usps_client):
        """Test carrier name is correct."""
        assert usps_client.carrier_name == "USPS"
    
    def test_calculate_rate_ground(self, usps_client):
        """Test ground rate calculation."""
        package = PackageInfo(weight=5.0, length=12.0, width=8.0, height=6.0)
        
        rate = usps_client.calculate_rate(
            origin_postal_code="90210",
            destination_postal_code="10001",
            package=package,
            service_level=ServiceLevel.GROUND,
        )
        
        assert rate.carrier_code == "usps"
        assert "GROUND" in rate.service_code
        assert rate.fuel_surcharge == 0.0  # USPS has no fuel surcharge
    
    def test_flat_rate_eligibility(self, usps_client):
        """Test flat rate box detection."""
        small_package = PackageInfo(weight=5.0, length=8.0, width=5.0, height=1.5)
        flat_rate_type = usps_client._check_flat_rate_eligible(small_package)
        
        assert flat_rate_type == "small_flat_rate_box"


class TestCarrierClientFactory:
    """Tests for carrier client factory."""
    
    def test_get_fedex_client(self):
        """Test getting FedEx client."""
        client = CarrierClientFactory.get_client("fedex")
        assert isinstance(client, FedExClient)
    
    def test_get_ups_client(self):
        """Test getting UPS client."""
        client = CarrierClientFactory.get_client("ups")
        assert isinstance(client, UPSClient)
    
    def test_get_usps_client(self):
        """Test getting USPS client."""
        client = CarrierClientFactory.get_client("usps")
        assert isinstance(client, USPSClient)
    
    def test_get_unknown_carrier_raises(self):
        """Test that unknown carrier raises error."""
        with pytest.raises(ValueError):
            CarrierClientFactory.get_client("unknown")
    
    def test_get_available_carriers(self):
        """Test getting available carrier list."""
        carriers = CarrierClientFactory.get_available_carriers()
        
        assert "fedex" in carriers
        assert "ups" in carriers
        assert "usps" in carriers
