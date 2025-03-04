import logging
from typing import Dict, List

import httpx
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


class InventoryService:
    """Client for interacting with the inventory service."""

    def __init__(self):
        self.base_url = settings.INVENTORY_SERVICE_URL

    async def reserve_inventory(self, order_id: str, items: List[Dict]) -> Dict:
        """Reserve inventory items for an order."""
        logger.info(f"Reserving inventory for order {order_id}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/inventory/reserve",
                    json={
                        "order_id": order_id,
                        "items": items,
                    },
                    timeout=10.0,
                )

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Inventory service error: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Inventory service error: {e.response.text}",
                )
            except httpx.RequestError as e:
                logger.error(f"Inventory request error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Inventory service unavailable: {str(e)}"
                )

    async def release_inventory(self, reservation_id: str) -> Dict:
        """Release reserved inventory."""
        logger.info(f"Releasing inventory reservation {reservation_id}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/inventory/release/{reservation_id}",
                    timeout=10.0,
                )

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Inventory release error: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Inventory release error: {e.response.text}",
                )
            except httpx.RequestError as e:
                logger.error(f"Inventory release request error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Inventory service unavailable during release: {str(e)}"
                )


inventory_service = InventoryService()
