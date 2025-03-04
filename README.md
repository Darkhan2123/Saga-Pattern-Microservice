# Saga Pattern Microservice

A practical implementation of the Saga Pattern for e-commerce checkout using FastAPI and Python.

## Overview

This project demonstrates the Saga Pattern in action, implementing a checkout workflow with three core services:

- **Payment Processing**: Handles customer payments and refunds
- **Inventory Management**: Manages product stock levels
- **Shipping**: Creates and cancels shipments

Each step supports both forward actions ("do") and compensating actions ("undo") to maintain data consistency.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Database

```bash
# Initialize Alembic
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

### 3. Start Services

```bash
python run_services.py
```

This starts all microservices:
- Main application: http://localhost:8000
- Payment service: http://localhost:8001
- Inventory service: http://localhost:8002
- Shipping service: http://localhost:8003

## Usage Example

### Create a New Order

```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust123",
    "items": [
      {"product_id": "product1", "name": "Product 1", "price": 10.0, "quantity": 2},
      {"product_id": "product2", "name": "Product 2", "price": 15.0, "quantity": 1}
    ],
    "shipping_address": {
      "street": "123 Main St",
      "city": "Cityville",
      "state": "State",
      "postal_code": "12345",
      "country": "Country"
    },
    "payment_method": "credit_card"
  }'
```

### Get Order Status

```bash
curl "http://localhost:8000/orders/{order_id}"
```

## Testing

Run tests with:

```bash
pytest
```

## How it Works

1. **Order Creation**: System creates database records for the order
2. **Step Execution**: Saga processes payment → reserves inventory → creates shipment
3. **Failure Handling**: If any step fails, the system executes compensating actions for all completed steps in reverse order
4. **Success**: When all steps complete, the order is marked as completed

## Key Features

- Persistent transaction state in database
- Real HTTP communication between services
- Comprehensive error handling
- Compensation tracking
- Fully tested with mocked services
