"""Tests for carrier client implementations."""
import pytest
from datetime import datetime, timedelta

from app.services.carrier_base import AddressInfo, PackageInfo, ServiceLevel
from app.services.fedex_client import FedExClient
from app.services.ups_client import UPSClient
from app.services.usps_client import USPSClient
from app.services.carrier_factory import CarrierClientFactory


class TestFedExClient:
    @pytest.fixture
    def fedex_client(self):
        return FedExClient()
    
    @pytest.fixture
    def sample_package(self):
        return PackageInfo(weight=5.0, length=12.0, width=8.0, height=6.0)
    
    def test_carrier_code(self, fedex_client):
        assert fedex_client.carrier_code == "fedex"
    
    def test_carrier_name(self, fedex_client):
        assert fedex_client.carrier_name == "FedEx"
    
    def test_calculate_zone_nearby(self, fedex_client):
        zone = fedex_client._calculate_zone("90210", "90220")
        assert zone == "1"
    
    def test_calculate_fuel_surcharge(self, fedex_client):
        surcharge = fedex_client._calculate_fuel_surcharge(100.0)
        assert surcharge == 12.0
    
    def test_calculate_rate_ground(self, fedex_client, sample_package):
        rate = fedex_client.calculate_rate("90210", "10001", sample_package, ServiceLevel.GROUND)
        
        assert rate.carrier_code == "fedex"
        assert rate.service_code == "FEDEX_GROUND"
        assert rate.total_cost > 0
        assert rate.fuel_surcharge > 0
        assert rate.estimated_delivery_days == 5
    
    def test_calculate_rate_overnight(self, fedex_client, sample_package):
        rate = fedex_client.calculate_rate("90210", "10001", sample_package, ServiceLevel.OVERNIGHT)
        
        assert rate.service_code == "FEDEX_PRIORITY_OVERNIGHT"
        assert rate.estimated_delivery_days == 1
        assert rate.guaranteed_delivery is True
    
    @pytest.mark.asyncio
    async def test_get_rates_all_services(self, fedex_client, sample_package):
        origin = AddressInfo(name="Test", address1="123 Main", city="LA", state="CA", postal_code="90210")
        destination = AddressInfo(name="Test", address1="456 Oak", city="NYC", state="NY", postal_code="10001")
        
        rates = await fedex_client.get_rates(origin, destination, [sample_package])
        assert len(rates) == 3


class TestUPSClient:
    @pytest.fixture
    def ups_client(self):
        return UPSClient()
    
    @pytest.fixture
    def sample_package(self):
        return PackageInfo(weight=5.0, length=12.0, width=8.0, height=6.0)
    
    def test_carrier_code(self, ups_client):
        assert ups_client.carrier_code == "ups"
    
    def test_calculate_rate_ground(self, ups_client, sample_package):
        rate = ups_client.calculate_rate("90210", "10001", sample_package, ServiceLevel.GROUND)
        
        assert rate.carrier_code == "ups"
        assert rate.service_code == "03"
        assert rate.total_cost > 0
    
    def test_hundredweight_discount(self, ups_client):
        heavy_package = PackageInfo(weight=120.0, length=12.0, width=8.0, height=6.0)
        rate = ups_client.calculate_rate("90210", "10001", heavy_package, ServiceLevel.GROUND)
        assert rate.total_cost > 0


class TestUSPSClient:
    @pytest.fixture
    def usps_client(self):
        return USPSClient()
    
    def test_carrier_code(self, usps_client):
        assert usps_client.carrier_code == "usps"
    
    def test_calculate_rate_ground(self, usps_client):
        package = PackageInfo(weight=5.0, length=12.0, width=8.0, height=6.0)
        rate = usps_client.calculate_rate("90210", "10001", package, ServiceLevel.GROUND)
        
        assert rate.carrier_code == "usps"
        assert "GROUND" in rate.service_code
        assert rate.fuel_surcharge == 0.0
    
    def test_flat_rate_eligibility(self, usps_client):
        small_package = PackageInfo(weight=5.0, length=8.0, width=5.0, height=1.5)
        flat_rate_type = usps_client._check_flat_rate_eligible(small_package)
        assert flat_rate_type == "small_flat_rate_box"


class TestCarrierClientFactory:
    def test_get_fedex_client(self):
        client = CarrierClientFactory.get_client("fedex")
        assert isinstance(client, FedExClient)
    
    def test_get_ups_client(self):
        client = CarrierClientFactory.get_client("ups")
        assert isinstance(client, UPSClient)
    
    def test_get_usps_client(self):
        client = CarrierClientFactory.get_client("usps")
        assert isinstance(client, USPSClient)
    
    def test_get_unknown_carrier_raises(self):
        with pytest.raises(ValueError):
            CarrierClientFactory.get_client("unknown")
    
    def test_get_available_carriers(self):
        carriers = CarrierClientFactory.get_available_carriers()
        assert "fedex" in carriers
        assert "ups" in carriers
        assert "usps" in carriers
