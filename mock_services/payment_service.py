from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import uuid
import uvicorn

app = FastAPI(title="Payment Service")

# In-memory storage for payments
payments = {}
refunds = {}


class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    payment_method: str


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    status: str
    transaction_id: str


class RefundResponse(BaseModel):
    refund_id: str
    payment_id: str
    amount: float
    status: str


@app.post("/payments", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest):
    # Validate payment request
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    # Check for insufficient funds (simulate a credit card decline)
    if request.amount > 1000:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    # Process payment
    payment_id = f"pay_{uuid.uuid4()}"
    transaction_id = f"trx_{uuid.uuid4()}"

    payment = {
        "payment_id": payment_id,
        "order_id": request.order_id,
        "amount": request.amount,
        "payment_method": request.payment_method,
        "status": "completed",
        "transaction_id": transaction_id
    }

    payments[payment_id] = payment

    return payment


@app.post("/payments/{payment_id}/refund", response_model=RefundResponse)
async def refund_payment(payment_id: str):
    # Check if payment exists
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment = payments[payment_id]

    # Check if payment was already refunded
    if payment["status"] == "refunded":
        raise HTTPException(status_code=400, detail="Payment already refunded")

    # Process refund
    refund_id = f"ref_{uuid.uuid4()}"

    refund = {
        "refund_id": refund_id,
        "payment_id": payment_id,
        "amount": payment["amount"],
        "status": "completed"
    }

    refunds[refund_id] = refund
    payment["status"] = "refunded"

    return refund


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    if payment_id not in payments:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payments[payment_id]


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
