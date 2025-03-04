import subprocess
import time
import os
import signal
import sys

services = [
    {"name": "Payment Service", "port": 8001, "file": "mock_services/payment_service.py"},
    {"name": "Inventory Service", "port": 8002, "file": "mock_services/inventory_service.py"},
    {"name": "Shipping Service", "port": 8003, "file": "mock_services/shipping_service.py"},
    {"name": "Main Application", "port": 8000, "file": "app/main.py"}
]

processes = []

def start_services():
    for service in services:
        print(f"Starting {service['name']} on port {service['port']}...")
        process = subprocess.Popen(
            ["uvicorn", service["file"].replace(".py", "").replace("/", ".") + ":app", "--host", "0.0.0.0", "--port", str(service["port"])],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(process)
        print(f"{service['name']} started with PID {process.pid}")
        time.sleep(1)  # Small delay to prevent port conflicts

def cleanup(sig=None, frame=None):
    print("Stopping all services...")
    for process in processes:
        process.terminate()

    for process in processes:
        process.wait()

    print("All services stopped.")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        start_services()
        print("All services are running. Press Ctrl+C to stop.")

        # Keep script running
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
        cleanup()
