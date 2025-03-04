from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import uvicorn

app = FastAPI(title="Shipping Service")

# In-memory storage for shipments
shipments = {}


class ShipmentRequest(BaseModel):
    order_id: str
    items: List[Dict]
    address: Dict


class ShipmentResponse(BaseModel):
    shipment_id: str
    order_id: str
    tracking_number: Optional[str]
    status: str
    estimated_delivery: Optional[str]


@app.post("/shipments", response_model=ShipmentResponse)
async def create_shipment(request: ShipmentRequest):
    # Validate address
    address = request.address
    if not all(key in address for key in ["street", "city", "state", "postal_code", "country"]):
        raise HTTPException(status_code=400, detail="Invalid shipping address")

    # Check for invalid postal code
    if address["postal_code"] == "00000":
        raise HTTPException(status_code=400, detail="Invalid postal code")

    # Create shipment
    shipment_id = f"ship_{uuid.uuid4()}"
    tracking_number = f"TRK{uuid.uuid4().hex[:12].upper()}"

    shipment = {
        "shipment_id": shipment_id,
        "order_id": request.order_id,
        "items": request.items,
        "address": address,
        "tracking_number": tracking_number,
        "status": "scheduled",
        "estimated_delivery": "2023-06-10"  # Example date
    }

    shipments[shipment_id] = shipment

    return shipment


@app.post("/shipments/{shipment_id}/cancel")
async def cancel_shipment(shipment_id: str):
    # Check if shipment exists
    if shipment_id not in shipments:
        raise HTTPException(status_code=404, detail="Shipment not found")

    shipment = shipments[shipment_id]

    # Check if already cancelled
    if shipment["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="Shipment already cancelled")

    # Check if already shipped
    if shipment["status"] == "shipped":
        raise HTTPException(status_code=400, detail="Cannot cancel shipped shipment")

    # Cancel shipment
    shipment["status"] = "cancelled"

    return {
        "shipment_id": shipment_id,
        "status": "cancelled",
        "message": "Shipment cancelled successfully"
    }


@app.get("/shipments/{shipment_id}")
async def get_shipment(shipment_id: str):
    if shipment_id not in shipments:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return shipments[shipment_id]


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
