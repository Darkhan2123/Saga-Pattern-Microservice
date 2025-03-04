import logging
from typing import Any, Dict, List, Type

from sqlalchemy.orm import Session

from app.models import Order, OrderStatus
from app.steps.base import Step

logger = logging.getLogger(__name__)


class Saga:
    """Saga coordinator that manages the execution of steps."""

    def __init__(self, db: Session, order: Order, step_classes: List[Type[Step]]):
        self.db = db
        self.order = order
        self.step_instances = []

        # Initialize steps with execution order
        for idx, step_class in enumerate(step_classes):
            step = step_class(db)
            step.register_step(order, idx + 1)
            self.step_instances.append(step)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all steps in the saga."""
        # Update order status to processing
        self.order.status = OrderStatus.PROCESSING
        self.db.commit()

        executed_steps = []

        try:
            for step in self.step_instances:
                logger.info(f"Executing step: {step.step_name}")
                context = await step.execute(context)
                executed_steps.append(step)

            # If all steps succeed, update order status to completed
            self.order.status = OrderStatus.COMPLETED
            self.db.commit()

            logger.info(f"Saga completed successfully for order {self.order.id}")
            return context

        except Exception as e:
            logger.error(f"Error executing saga for order {self.order.id}: {str(e)}")

            # Update order status to failed
            self.order.status = OrderStatus.FAILED
            self.db.commit()

            # Compensate executed steps in reverse order
            await self.compensate(context, executed_steps)

            # Re-raise the exception
            raise

    async def compensate(self, context: Dict[str, Any], steps_to_compensate=None) -> Dict[str, Any]:
        """
        Compensate for executed steps in reverse order.
        If steps_to_compensate is not provided, compensate all executed steps.
        """
        steps = steps_to_compensate if steps_to_compensate is not None else self.step_instances

        for step in reversed(steps):
            try:
                logger.info(f"Compensating step: {step.step_name}")
                context = await step.compensate(context)
            except Exception as e:
                logger.error(f"Error compensating step {step.step_name}: {str(e)}")
                # Continue compensating other steps even if one fails

        return context
