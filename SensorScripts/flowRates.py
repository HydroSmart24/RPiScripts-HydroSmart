import serial
import time
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Path to the Firebase service account JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), '..', 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Open serial port
ser = serial.Serial('/dev/ttyACM0', 9600)  # Adjust the port and baud rate as needed

# Variables to track flow and time
flow_started = False
start_time = 0
total_flow = 0.0

def update_firebase(consumed_amount):
    """Update Firebase with the consumed amount and timestamp."""
    doc_ref = db.collection('dailyConsumption').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'consumed_liters': consumed_amount
    })

while True:
    line = ser.readline().decode('utf-8').strip()

    if 'Flow rate:' in line:
        try:
            # Extract flow rate
            flow_rate_str = line.split('Flow rate: ')[1].split(' L/min')[0]
            flow_rate = float(flow_rate_str)

            # Print the current flow rate reading
            print(f"Current Flow Rate: {flow_rate} L/min")

            if flow_rate > 0 and not flow_started:
                # Start the timer
                start_time = time.time()
                flow_started = True
                total_flow = 0.0

            if flow_started:
                # Calculate elapsed time in minutes
                elapsed_time = (time.time() - start_time) / 60.0
                # Add the flow during this time to the total flow
                total_flow += flow_rate * elapsed_time
                # Reset start time for the next interval
                start_time = time.time()

            if flow_rate == 0 and flow_started:
                # Stop the timer and finalize the flow calculation
                flow_started = False
                if total_flow > 0:
                    print(f"Total consumed: {total_flow:.2f} liters")
                    update_firebase(total_flow)
                total_flow = 0.0

        except (ValueError, IndexError):
            # Handle any potential parsing errors
            print("Received invalid flow rate data:", line)
