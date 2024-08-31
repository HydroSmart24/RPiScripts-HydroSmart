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
last_flow_rate = 0.0

# Variable to track time for distance updates
distance_start_time = time.time()
last_distance = 0.0

def update_firebase(consumed_amount):
    doc_ref = db.collection('dailyConsumption').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'consumed_liters': round(consumed_amount, 2)  # Ensure the value is rounded to 2 decimal places
    })

def send_distance_to_firebase(distance):
    doc_ref = db.collection('avgDistance').document()
    doc_ref.set({
        'time': firestore.SERVER_TIMESTAMP,
        'distance': round(distance, 2)
    })
    print(f"Distance {distance:.2f} cm sent to Firebase")

def detect_leakage():
    doc_ref = db.collection('leakageDetect').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'status': 'detected'
    })
    print("Leakage detected and reported to Firebase")

while True:
    line = ser.readline().decode('utf-8').strip()

    try:
        if 'Flow rate:' in line:
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
                    total_flow = round(total_flow, 2)  # Round the total flow to 2 decimal places
                    print(f"Total consumed: {total_flow:.2f} liters")
                    update_firebase(total_flow)
                    print("Consumption sent to Database")  # Print after sending to Firebase
                total_flow = 0.0

            # Update the last flow rate
            last_flow_rate = flow_rate

        elif 'Distance:' in line:
            # Extract distance
            distance_str = line.split('Distance: ')[1].split(' cm')[0]
            distance = float(distance_str)

            # Print the current distance reading
            print(f"Current Distance: {distance} cm")

            # Check if 5 minutes have passed to send the distance to Firebase
            if (time.time() - distance_start_time) >= 300:
                send_distance_to_firebase(distance)
                distance_start_time = time.time()  # Reset the timer for the next 5-minute interval

            # Detect significant distance increase with no flow (leakage detection)
            if last_flow_rate == 0 and (distance - last_distance) > 5:  # Adjust the threshold as needed
                detect_leakage()

            # Update the last distance
            last_distance = distance

    except (ValueError, IndexError):
        # Handle any potential parsing errors
        print("Received invalid data:", line)
