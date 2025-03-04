import logging
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.models import (AddressCreate, ItemCreate, Order, OrderCreate,
                        OrderItem, OrderResponse, OrderStatus, ShippingAddress)
from app.saga import Saga
from app.steps.inventory import InventoryStep
from app.steps.payment import PaymentStep
from app.steps.shipping import ShippingStep

# Create database tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Saga Pattern Microservice")


@app.post("/orders", response_model=OrderResponse)
async def create_order(request: OrderCreate, db: Session = Depends(get_db)):
    """Create a new order and execute the checkout saga."""
    try:
        # Calculate total amount
        total_amount = sum(item.price * item.quantity for item in request.items)

        # Create order
        order = Order(
            customer_id=request.customer_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
        )
        db.add(order)
        db.flush()  # Flush to get the order ID

        # Add order items
        order_items = []
        for item in request.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
            )
            db.add(order_item)
            order_items.append(order_item)

        # Add shipping address
        shipping_address = ShippingAddress(
            order_id=order.id,
            **request.shipping_address.dict()
        )
        db.add(shipping_address)

        # Add payment info
        payment_info = models.PaymentInfo(
            order_id=order.id,
            payment_method=request.payment_method,
        )
        db.add(payment_info)

        db.commit()
        db.refresh(order)

        # Prepare context for saga
        context = {
            "order_id": order.id,
            "customer_id": order.customer_id,
            "total_amount": order.total_amount,
            "payment_method": request.payment_method,
            "shipping_address": request.shipping_address.dict(),
            "items": [
                {
                    "product_id": item.product_id,
                    "name": item.name,
                    "price": item.price,
                    "quantity": item.quantity,
                }
                for item in request.items
            ],
        }

        # Create and execute saga
        saga = Saga(
            db,
            order,
            [PaymentStep, InventoryStep, ShippingStep]
        )

        try:
            await saga.execute(context)

            # Refresh order to get the latest state
            db.refresh(order)
            return order

        except Exception as e:
            # Note: The saga already updates the order status, so we don't need to do it here
            raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get order details."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
