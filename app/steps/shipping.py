import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models import StepStatus
from app.services.shipping import shipping_service
from app.steps.base import Step

logger = logging.getLogger(__name__)


class ShippingStep(Step):
    """Step to process shipping."""

    def __init__(self, db: Session):
        super().__init__(db, step_name="shipping")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process shipping for the order."""
        order_id = context["order_id"]
        items = context["items"]
        shipping_address = context["shipping_address"]

        logger.info(f"Executing shipping step for order {order_id}")

        try:
            # Call shipping service
            shipping_result = await shipping_service.create_shipment(
                order_id, items, shipping_address
            )

            # Update step status
            self.update_step_status(
                StepStatus.COMPLETED,
                reference_id=shipping_result["shipment_id"]
            )

            # Update context with shipping information
            context["shipment_id"] = shipping_result["shipment_id"]
            context["tracking_number"] = shipping_result.get("tracking_number")

            return context

        except Exception as e:
            error_message = str(e)
            logger.error(f"Shipping step failed: {error_message}")

            # Update step status to failed
            self.update_step_status(
                StepStatus.FAILED,
                error_message=error_message
            )

            raise

    async def compensate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel the shipping."""
        shipment_id = context.get("shipment_id")
        if not shipment_id:
            logger.warning("No shipment to cancel")
            return context

        logger.info(f"Compensating shipping step for shipment {shipment_id}")

        try:
            # Call shipping service to cancel
            cancel_result = await shipping_service.cancel_shipment(shipment_id)

            # Update step status
            self.update_step_status(
                StepStatus.COMPENSATED,
                reference_id=shipment_id
            )

            # Update context
            context["shipping_status"] = "cancelled"

            return context

        except Exception as e:
            error_message = str(e)
            logger.error(f"Shipping compensation failed: {error_message}")

            # Even if compensation fails, we still mark it as attempted
            self.update_step_status(
                StepStatus.FAILED,
                error_message=f"Compensation failed: {error_message}"
            )

            # We don't re-raise the exception here to allow other compensations to proceed
            return context
