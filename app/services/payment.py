import logging
from typing import Dict, Optional

import httpx
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    """Client for interacting with the payment service."""

    def __init__(self):
        self.base_url = settings.PAYMENT_SERVICE_URL

    async def process_payment(
        self, order_id: str, amount: float, payment_method: str
    ) -> Dict:
        """Process a payment through the payment service."""
        logger.info(f"Processing payment for order {order_id}: ${amount}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/payments",
                    json={
                        "order_id": order_id,
                        "amount": amount,
                        "payment_method": payment_method,
                    },
                    timeout=10.0,
                )

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Payment service error: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Payment service error: {e.response.text}",
                )
            except httpx.RequestError as e:
                logger.error(f"Payment request error: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Payment service unavailable: {str(e)}"
                )

    async def refund_payment(self, payment_id: str) -> Dict:
        """Refund a payment through the payment service."""
        logger.info(f"Refunding payment {payment_id}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/payments/{payment_id}/refund",
                    timeout=10.0,
                )

                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Payment refund error: {e.response.text}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Payment refund error: {e.response.text}",
                )
            except httpx.RequestError as e:
                logger.error(f"Payment refund request error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Payment service unavailable during refund: {str(e)}"
                )


payment_service = PaymentService()
