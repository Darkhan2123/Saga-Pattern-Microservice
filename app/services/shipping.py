import logging
from typing import Dict

import httpx
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


class ShippingService:
    """Client for interacting with the shipping service."""

    def __init__(self):
        self.base_url = settings.SHIPPING_SERVICE_URL

    async def create_shipment(
        self, order_id: str, items: Dict, address: Dict
    ) -> Dict:
        """Create a shipment for an order."""
        logger.info(f"Creating shipment for order {order_id}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/shipments",
                    json={
                        "order_id": order_id,
                        "items": items,
                        "address": address,
                    },
                    timeout=10.0,
                )

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Shipping service error: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Shipping service error: {e.response.text}",
                )
            except httpx.RequestError as e:
                logger.error(f"Shipping request error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Shipping service unavailable: {str(e)}"
                )

    async def cancel_shipment(self, shipment_id: str) -> Dict:
        """Cancel a shipment."""
        logger.info(f"Cancelling shipment {shipment_id}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/shipments/{shipment_id}/cancel",
                    timeout=10.0,
                )

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Shipping cancellation error: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Shipping cancellation error: {e.response.text}",
                )
            except httpx.RequestError as e:
                logger.error(f"Shipping cancellation request error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Shipping service unavailable during cancellation: {str(e)}"
                )


shipping_service = ShippingService()
