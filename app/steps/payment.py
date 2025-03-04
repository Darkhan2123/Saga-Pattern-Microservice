import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models import Order, PaymentInfo, StepStatus
from app.services.payment import payment_service
from app.steps.base import Step

logger = logging.getLogger(__name__)


class PaymentStep(Step):
    """Step to process payment."""

    def __init__(self, db: Session):
        super().__init__(db, step_name="payment")

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for the order."""
        order_id = context["order_id"]
        amount = context["total_amount"]
        payment_method = context["payment_method"]

        logger.info(f"Executing payment step for order {order_id}")

        try:
            # Call payment service
            payment_result = await payment_service.process_payment(
                order_id, amount, payment_method
            )

            # Update order with payment info
            payment_info = PaymentInfo(
                order_id=order_id,
                payment_method=payment_method,
                payment_id=payment_result["payment_id"],
                transaction_id=payment_result["transaction_id"],
            )
            self.db.add(payment_info)

            # Update step status
            self.update_step_status(
                StepStatus.COMPLETED,
                reference_id=payment_result["payment_id"]
            )

            # Update context with payment information
            context["payment_id"] = payment_result["payment_id"]
            context["transaction_id"] = payment_result["transaction_id"]

            self.db.commit()
            return context

        except Exception as e:
            error_message = str(e)
            logger.error(f"Payment step failed: {error_message}")

            # Update step status to failed
            self.update_step_status(
                StepStatus.FAILED,
                error_message=error_message
            )

            raise

    async def compensate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Refund the payment."""
        payment_id = context.get("payment_id")
        if not payment_id:
            logger.warning("No payment to refund")
            return context

        logger.info(f"Compensating payment step for payment {payment_id}")

        try:
            # Call payment service for refund
            refund_result = await payment_service.refund_payment(payment_id)

            # Update step status
            self.update_step_status(
                StepStatus.COMPENSATED,
                reference_id=refund_result.get("refund_id")
            )

            # Update context
            context["refund_id"] = refund_result.get("refund_id")
            context["payment_status"] = "refunded"

            return context

        except Exception as e:
            error_message = str(e)
            logger.error(f"Payment compensation failed: {error_message}")

            # Even if compensation fails, we still mark it as attempted
            self.update_step_status(
                StepStatus.FAILED,
                error_message=f"Compensation failed: {error_message}"
            )

            # We don't re-raise the exception here to allow other compensations to proceed
            return context
