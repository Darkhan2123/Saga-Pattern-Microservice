import abc
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models import Order, OrderStep, StepStatus

logger = logging.getLogger(__name__)


class Step(abc.ABC):
    """Base class for all steps in the saga."""

    def __init__(self, db: Session, step_name: str):
        self.db = db
        self.step_name = step_name
        self.order_step = None

    def register_step(self, order: Order, execution_order: int) -> OrderStep:
        """Register this step with the order."""
        order_step = OrderStep(
            order_id=order.id,
            step_name=self.step_name,
            execution_order=execution_order,
            status=StepStatus.PENDING,
        )
        self.db.add(order_step)
        self.db.commit()
        self.db.refresh(order_step)
        self.order_step = order_step
        return order_step

    def update_step_status(
        self, status: StepStatus, reference_id: Optional[str] = None, error_message: Optional[str] = None
    ) -> OrderStep:
        """Update the status of this step."""
        if not self.order_step:
            raise ValueError("Step not registered")

        self.order_step.status = status
        if reference_id:
            self.order_step.reference_id = reference_id
        if error_message:
            self.order_step.error_message = error_message

        self.db.commit()
        self.db.refresh(self.order_step)
        return self.order_step

    @abc.abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the step and return updated context."""
        pass

    @abc.abstractmethod
    async def compensate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compensate for the step and return updated context."""
        pass
