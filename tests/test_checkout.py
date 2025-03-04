import pytest
from unittest.mock import AsyncMock, patch
from httpx import HTTPStatusError, Response

from app.services.payment import payment_service
from app.services.inventory import inventory_service
from app.services.shipping import shipping_service


@pytest.fixture
def order_request():
    return {
        "customer_id": "cust123",
        "items": [
            {"product_id": "product1", "name": "Product 1", "price": 10.0, "quantity": 2},
            {"product_id": "product2", "name": "Product 2", "price": 15.0, "quantity": 1}
        ],
        "shipping_address": {
            "street": "123 Main St",
            "city": "Cityville",
            "state": "Stateland",
            "postal_code": "12345",
            "country": "Country"
        },
        "payment_method": "credit_card"
    }


@pytest.mark.asyncio
async def test_successful_checkout(client, order_request):
    """Test a successful checkout process with all steps succeeding."""
    # Mock external service calls
    with patch.object(
        payment_service, "process_payment", new_callable=AsyncMock
    ) as mock_payment, patch.object(
        inventory_service, "reserve_inventory", new_callable=AsyncMock
    ) as mock_inventory, patch.object(
        shipping_service, "create_shipment", new_callable=AsyncMock
    ) as mock_shipping:

        # Setup mock responses
        mock_payment.return_value = {
            "payment_id": "pay_123",
            "transaction_id": "trx_123",
            "status": "completed"
        }

        mock_inventory.return_value = {
            "reservation_id": "res_123",
            "status": "reserved"
        }

        mock_shipping.return_value = {
            "shipment_id": "ship_123",
            "tracking_number": "TRK123",
            "status": "scheduled"
        }

        # Send checkout request
        response = client.post("/orders", json=order_request)

        # Check response
        assert response.status_code == 200
        data = response.json()

        # Verify order status
        assert data["status"] == "completed"

        # Verify payment info
        assert data["payment_info"]["payment_id"] == "pay_123"
        assert data["payment_info"]["transaction_id"] == "trx_123"

        # Verify steps were executed
        payment_step = next((s for s in data["steps"] if s["step_name"] == "payment"), None)
        inventory_step = next((s for s in data["steps"] if s["step_name"] == "inventory"), None)
        shipping_step = next((s for s in data["steps"] if s["step_name"] == "shipping"), None)

        assert payment_step["status"] == "completed"
        assert inventory_step["status"] == "completed"
        assert shipping_step["status"] == "completed"

        # Verify service calls
        mock_payment.assert_called_once()
        mock_inventory.assert_called_once()
        mock_shipping.assert_called_once()


@pytest.mark.asyncio
async def test_payment_failure(client, order_request):
    """Test compensation when payment fails."""
    # Mock external service calls with payment failing
    with patch.object(
        payment_service, "process_payment", new_callable=AsyncMock
    ) as mock_payment:

        # Setup mock responses - payment fails
        mock_payment.side_effect = HTTPStatusError(
            "Payment failed: Insufficient funds",
            request=None,
            response=Response(400, content="Insufficient funds")
        )

        # Send checkout request
        response = client.post("/orders", json=order_request)

        # Check response
        assert response.status_code == 400

        # Verify order status by getting the order
        order_id = client.get("/orders").json()[0]["id"]
        order = client.get(f"/orders/{order_id}").json()

        assert order["status"] == "failed"

        # Verify payment step failed
        payment_step = next((s for s in order["steps"] if s["step_name"] == "payment"), None)
        assert payment_step["status"] == "failed"

        # No other steps should be executed
        assert len([s for s in order["steps"] if s["status"] == "completed"]) == 0


@pytest.mark.asyncio
async def test_inventory_failure_with_payment_compensation(client, order_request):
    """Test compensation when inventory fails after payment succeeds."""
    # Mock external service calls
    with patch.object(
        payment_service, "process_payment", new_callable=AsyncMock
    ) as mock_payment, patch.object(
        payment_service, "refund_payment", new_callable=AsyncMock
    ) as mock_refund, patch.object(
        inventory_service, "reserve_inventory", new_callable=AsyncMock
    ) as mock_inventory:

        # Setup mock responses
        mock_payment.return_value = {
            "payment_id": "pay_123",
            "transaction_id": "trx_123",
            "status": "completed"
        }

        # Inventory fails
        mock_inventory.side_effect = HTTPStatusError(
            "Inventory failed: Out of stock",
            request=None,
            response=Response(400, content="Out of stock")
        )

        # Refund succeeds
        mock_refund.return_value = {
            "refund_id": "ref_123",
            "status": "completed"
        }

        # Send checkout request
        response = client.post("/orders", json=order_request)

        # Check response
        assert response.status_code == 400

        # Verify order status
        order_id = client.get("/orders").json()[0]["id"]
        order = client.get(f"/orders/{order_id}").json()

        assert order["status"] == "failed"

        # Verify payment was completed and then compensated
        payment_step = next((s for s in order["steps"] if s["step_name"] == "payment"), None)
        assert payment_step["status"] == "compensated"

        # Verify inventory step failed
        inventory_step = next((s for s in order["steps"] if s["step_name"] == "inventory"), None)
        assert inventory_step["status"] == "failed"

        # Verify services were called correctly
        mock_payment.assert_called_once()
        mock_inventory.assert_called_once()
        mock_refund.assert_called_once_with("pay_123")


@pytest.mark.asyncio
async def test_shipping_failure_with_compensation(client, order_request):
    """Test compensation when shipping fails after payment and inventory succeed."""
    # Mock external service calls
    with patch.object(
        payment_service, "process_payment", new_callable=AsyncMock
    ) as mock_payment, patch.object(
        payment_service, "refund_payment", new_callable=AsyncMock
    ) as mock_refund, patch.object(
        inventory_service, "reserve_inventory", new_callable=AsyncMock
    ) as mock_inventory, patch.object(
        inventory_service, "release_inventory", new_callable=AsyncMock
    ) as mock_release, patch.object(
        shipping_service, "create_shipment", new_callable=AsyncMock
    ) as mock_shipping:

        # Setup mock responses
        mock_payment.return_value = {
            "payment_id": "pay_123",
            "transaction_id": "trx_123",
            "status": "completed"
        }

        mock_inventory.return_value = {
            "reservation_id": "res_123",
            "status": "reserved"
        }

        # Shipping fails
        mock_shipping.side_effect = HTTPStatusError(
            "Shipping failed: Invalid postal code",
            request=None,
            response=Response(400, content="Invalid postal code")
        )

        # Compensation succeeds
        mock_refund.return_value = {
            "refund_id": "ref_123",
            "status": "completed"
        }

        mock_release.return_value = {
            "status": "released"
        }

        # Send checkout request
        response = client.post("/orders", json=order_request)

        # Check response
        assert response.status_code == 400

        # Verify order status
        order_id = client.get("/orders").json()[0]["id"]
        order = client.get(f"/orders/{order_id}").json()

        assert order["status"] == "failed"

        # Verify steps statuses
        payment_step = next((s for s in order["steps"] if s["step_name"] == "payment"), None)
        inventory_step = next((s for s in order["steps"] if s["step_name"] == "inventory"), None)
        shipping_step = next((s for s in order["steps"] if s["step_name"] == "shipping"), None)

        assert payment_step["status"] == "compensated"
        assert inventory_step["status"] == "compensated"
        assert shipping_step["status"] == "failed"

        # Verify services were called correctly
        mock_payment.assert_called_once()
        mock_inventory.assert_called_once()
        mock_shipping.assert_called_once()
        mock_refund.assert_called_once_with("pay_123")
        mock_release.assert_called_once_with("res_123")
