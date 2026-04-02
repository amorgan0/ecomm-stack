"""Tests for rate calculator module."""
import pytest

from app.services.carrier_base import (
    AddressInfo,
    PackageInfo,
    ServiceLevel,
)
from app.services.rate_calculator import RateCalculator


class TestRateCalculator:
    """Tests for RateCalculator class."""
    
    @pytest.fixture
    def rate_calculator(self):
        """Create rate calculator instance."""
        return RateCalculator()
    
    @pytest.fixture
    def sample_origin(self):
        """Create sample origin address."""
        return AddressInfo(
            name="Warehouse",
            address1="123 Shipping Lane",
            city="Los Angeles",
            state="CA",
            postal_code="90210",
        )
    
    @pytest.fixture
    def sample_destination(self):
        """Create sample destination address."""
        return AddressInfo(
            name="John Doe",
            address1="456 Main St",
            city="New York",
            state="NY",
            postal_code="10001",
        )
    
    @pytest.fixture
    def medium_package(self):
        """Create medium package."""
        return PackageInfo(weight=10.0, length=14.0, width=10.0, height=8.0)
    
    def test_calculate_rates_all_carriers(self, rate_calculator, sample_origin, sample_destination, medium_package):
        """Test calculating rates for all carriers."""
        rates = rate_calculator.calculate_rates(
            origin=sample_origin,
            destination=sample_destination,
            packages=[medium_package],
        )
        
        assert "fedex" in rates
        assert "ups" in rates
        assert "usps" in rates
        
        for carrier_rates in rates.values():
            assert len(carrier_rates) > 0
    
    def test_get_cheapest_rate(self, rate_calculator, sample_origin, sample_destination, medium_package):
        """Test getting cheapest rate."""
        cheapest = rate_calculator.get_cheapest_rate(
            origin=sample_origin,
            destination=sample_destination,
            packages=[medium_package],
        )
        
        assert cheapest is not None
        assert cheapest.total_cost > 0
    
    def test_get_fastest_rate(self, rate_calculator, sample_origin, sample_destination, medium_package):
        """Test getting fastest delivery rate."""
        fastest = rate_calculator.get_fastest_rate(
            origin=sample_origin,
            destination=sample_destination,
            packages=[medium_package],
        )
        
        assert fastest is not None
        assert fastest.estimated_delivery_days == 1  # Overnight
    
    def test_get_best_value_rate(self, rate_calculator, sample_origin, sample_destination, medium_package):
        """Test getting best value rate."""
        best = rate_calculator.get_best_value_rate(
            origin=sample_origin,
            destination=sample_destination,
            packages=[medium_package],
        )
        
        assert best is not None
        assert best.total_cost > 0
    
    def test_specific_carriers_only(self, sample_origin, sample_destination, medium_package):
        """Test calculator with limited carriers."""
        calculator = RateCalculator(carriers=["fedex", "ups"])
        
        rates = calculator.calculate_rates(
            origin=sample_origin,
            destination=sample_destination,
            packages=[medium_package],
        )
        
        assert "fedex" in rates
        assert "ups" in rates
        assert "usps" not in rates


class TestCarrierSpecificPricing:
    """Tests for carrier-specific pricing rules."""
    
    @pytest.fixture
    def origin(self):
        """Create origin address."""
        return AddressInfo(
            name="Warehouse",
            address1="123 Shipping Lane",
            city="Los Angeles",
            state="CA",
            postal_code="90210",
        )
    
    @pytest.fixture
    def destination(self):
        """Create destination address."""
        return AddressInfo(
            name="Customer",
            address1="456 Main St",
            city="New York",
            state="NY",
            postal_code="10001",
        )
    
    def test_fedex_fuel_surcharge(self, origin, destination):
        """Test FedEx fuel surcharge is applied."""
        from app.services.fedex_client import FedExClient
        
        client = FedExClient()
        package = PackageInfo(weight=10.0, length=12.0, width=8.0, height=6.0)
        
        rate = client.calculate_rate(
            origin_postal_code=origin.postal_code,
            destination_postal_code=destination.postal_code,
            package=package,
            service_level=ServiceLevel.GROUND,
        )
        
        assert rate.fuel_surcharge > 0
    
    def test_usps_no_fuel_surcharge(self, origin, destination):
        """Test USPS has no fuel surcharge."""
        from app.services.usps_client import USPSClient
        
        client = USPSClient()
        package = PackageInfo(weight=10.0, length=12.0, width=8.0, height=6.0)
        
        rate = client.calculate_rate(
            origin_postal_code=origin.postal_code,
            destination_postal_code=destination.postal_code,
            package=package,
            service_level=ServiceLevel.GROUND,
        )
        
        assert rate.fuel_surcharge == 0.0


class TestServiceLevelPricing:
    """Tests for service level pricing differences."""
    
    @pytest.fixture
    def package(self):
        """Create sample package."""
        return PackageInfo(weight=10.0, length=12.0, width=8.0, height=6.0)
    
    @pytest.fixture
    def origin_zip(self):
        """Origin ZIP code."""
        return "90210"
    
    @pytest.fixture
    def dest_zip(self):
        """Destination ZIP code."""
        return "10001"
    
    def test_fedex_service_level_price_difference(self, package, origin_zip, dest_zip):
        """Test FedEx prices increase with faster service levels."""
        from app.services.fedex_client import FedExClient
        
        client = FedExClient()
        
        ground = client.calculate_rate(origin_zip, dest_zip, package, ServiceLevel.GROUND)
        express = client.calculate_rate(origin_zip, dest_zip, package, ServiceLevel.EXPRESS)
        overnight = client.calculate_rate(origin_zip, dest_zip, package, ServiceLevel.OVERNIGHT)
        
        # Price should increase with speed
        assert ground.total_cost < express.total_cost
        assert express.total_cost < overnight.total_cost
    
    def test_overnight_guaranteed_delivery(self, package, origin_zip, dest_zip):
        """Test overnight services have guaranteed delivery."""
        from app.services.fedex_client import FedExClient
        from app.services.ups_client import UPSClient
        from app.services.usps_client import USPSClient
        
        fedex = FedExClient()
        ups = UPSClient()
        usps = USPSClient()
        
        fedex_overnight = fedex.calculate_rate(origin_zip, dest_zip, package, ServiceLevel.OVERNIGHT)
        ups_overnight = ups.calculate_rate(origin_zip, dest_zip, package, ServiceLevel.OVERNIGHT)
        usps_overnight = usps.calculate_rate(origin_zip, dest_zip, package, ServiceLevel.OVERNIGHT)
        
        # All overnight should be guaranteed
        assert fedex_overnight.guaranteed_delivery is True
        assert ups_overnight.guaranteed_delivery is True
        assert usps_overnight.guaranteed_delivery is True
