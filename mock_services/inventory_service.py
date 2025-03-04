from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import uvicorn

app = FastAPI(title="Inventory Service")

# In-memory storage for inventory and reservations
inventory = {
    "product1": {"name": "Product 1", "quantity": 100},
    "product2": {"name": "Product 2", "quantity": 50},
    "product3": {"name": "Product 3", "quantity": 0},  # Out of stock
}

reservations = {}


class InventoryItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int


class ReservationRequest(BaseModel):
    order_id: str
    items: List[Dict]


class ReservationResponse(BaseModel):
    reservation_id: str
    order_id: str
    items: List[Dict]
    status: str


@app.post("/inventory/reserve", response_model=ReservationResponse)
async def reserve_inventory(request: ReservationRequest):
    # Check if we have enough inventory for each item
    for item in request.items:
        product_id = item["product_id"]
        quantity = item["quantity"]

        # Check if product exists
        if product_id not in inventory:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

        # Check if enough stock
        if inventory[product_id]["quantity"] < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product_id}. Requested: {quantity}, Available: {inventory[product_id]['quantity']}"
            )

    # Reserve inventory
    reservation_id = f"res_{uuid.uuid4()}"

    # Update inventory
    reserved_items = []
    for item in request.items:
        product_id = item["product_id"]
        quantity = item["quantity"]

        inventory[product_id]["quantity"] -= quantity
        reserved_items.append({
            "product_id": product_id,
            "quantity": quantity
        })

    reservation = {
        "reservation_id": reservation_id,
        "order_id": request.order_id,
        "items": reserved_items,
        "status": "reserved"
    }

    reservations[reservation_id] = reservation

    return reservation


@app.post("/inventory/release/{reservation_id}")
async def release_inventory(reservation_id: str):
    # Check if reservation exists
    if reservation_id not in reservations:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation = reservations[reservation_id]

    # Check if already released
    if reservation["status"] == "released":
        raise HTTPException(status_code=400, detail="Reservation already released")

    # Release inventory
    for item in reservation["items"]:
        product_id = item["product_id"]
        quantity = item["quantity"]

        inventory[product_id]["quantity"] += quantity

    # Update reservation status
    reservation["status"] = "released"

    return {
        "reservation_id": reservation_id,
        "status": "released",
        "message": "Inventory released successfully"
    }


@app.get("/inventory/{product_id}")
async def get_inventory(product_id: str):
    if product_id not in inventory:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "product_id": product_id,
        "quantity": inventory[product_id]["quantity"],
        "name": inventory[product_id]["name"]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
