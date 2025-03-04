import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models import OrderItem, StepStatus
from app.services.inventory import inventory_service
from app.steps.base import Step

logger = logging.getLogger(__name__)


class InventoryStep(Step):
    """Step to reserve inventory."""

    def __init__(self, db: Session):
        super().__init__(db, step_name="inventory")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Reserve inventory items for the order."""
        order_id = context["order_id"]
        items = context["items"]

        logger.info(f"Executing inventory step for order {order_id}")

        try:
            # Call inventory service
            inventory_result = await inventory_service.reserve_inventory(
                order_id, items
            )

            # Update step status
            self.update_step_status(
                StepStatus.COMPLETED,
                reference_id=inventory_result["reservation_id"]
            )

            # Update context with reservation information
            context["reservation_id"] = inventory_result["reservation_id"]

            return context

        except Exception as e:
            error_message = str(e)
            logger.error(f"Inventory step failed: {error_message}")

            # Update step status to failed
            self.update_step_status(
                StepStatus.FAILED,
                error_message=error_message
            )

            raise

    async def compensate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Release reserved inventory."""
        reservation_id = context.get("reservation_id")
        if not reservation_id:
            logger.warning("No inventory reservation to release")
            return context

        logger.info(f"Compensating inventory step for reservation {reservation_id}")

        try:
            # Call inventory service to release
            release_result = await inventory_service.release_inventory(reservation_id)

            # Update step status
            self.update_step_status(
                StepStatus.COMPENSATED,
                reference_id=reservation_id
            )

            # Update context
            context["inventory_status"] = "released"

            return context

        except Exception as e:
            error_message = str(e)
            logger.error(f"Inventory compensation failed: {error_message}")

            # Even if compensation fails, we still mark it as attempted
            self.update_step_status(
                StepStatus.FAILED,
                error_message=f"Compensation failed: {error_message}"
            )

            # We don't re-raise the exception here to allow other compensations to proceed
            return context
