from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import (Column, DateTime, Enum, Float, ForeignKey, Integer,
                        String, Table)
from sqlalchemy.orm import relationship

from app.database import Base


# SQLAlchemy Models
class OrderStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    customer_id = Column(String, index=True)
    total_amount = Column(Float)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("OrderItem", back_populates="order")
    steps = relationship("OrderStep", back_populates="order")
    shipping_address = relationship("ShippingAddress", back_populates="order", uselist=False)
    payment_info = relationship("PaymentInfo", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"))
    product_id = Column(String, index=True)
    name = Column(String)
    price = Column(Float)
    quantity = Column(Integer)

    # Relationships
    order = relationship("Order", back_populates="items")


class ShippingAddress(Base):
    __tablename__ = "shipping_addresses"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), unique=True)
    street = Column(String)
    city = Column(String)
    state = Column(String)
    postal_code = Column(String)
    country = Column(String)

    # Relationships
    order = relationship("Order", back_populates="shipping_address")


class PaymentInfo(Base):
    __tablename__ = "payment_info"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"), unique=True)
    payment_method = Column(String)
    payment_id = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="payment_info")


class OrderStep(Base):
    __tablename__ = "order_steps"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    order_id = Column(String, ForeignKey("orders.id"))
    step_name = Column(String)
    status = Column(Enum(StepStatus), default=StepStatus.PENDING)
    execution_order = Column(Integer)
    reference_id = Column(String, nullable=True)  # External reference ID (e.g., payment_id)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="steps")


# Pydantic Models
class ItemCreate(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = 1


class AddressCreate(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str


class OrderCreate(BaseModel):
    customer_id: str
    items: List[ItemCreate]
    shipping_address: AddressCreate
    payment_method: str = "credit_card"


class ItemResponse(BaseModel):
    id: str
    product_id: str
    name: str
    price: float
    quantity: int

    class Config:
        orm_mode = True


class AddressResponse(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    country: str

    class Config:
        orm_mode = True


class PaymentResponse(BaseModel):
    payment_method: str
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None

    class Config:
        orm_mode = True


class StepResponse(BaseModel):
    step_name: str
    status: StepStatus
    execution_order: int
    reference_id: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        orm_mode = True


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    total_amount: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    items: List[ItemResponse]
    shipping_address: AddressResponse
    payment_info: PaymentResponse
    steps: List[StepResponse]

    class Config:
        orm_mode = True
