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
    print(f"---------------Distance {distance:.2f} cm sent to Firebase---------------")

def detect_leakage():
    doc_ref = db.collection('leakageDetect').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'status': 'detected'
    })
    print("---------------Leakage detected and reported---------------")

while True:
    line = ser.readline().decode('utf-8').strip()

    try:
        # Handle flow rate
        if 'Flow rate:' in line:
            flow_rate_str = line.split('Flow rate: ')[1].split(' L/min')[0]
            flow_rate = float(flow_rate_str)
            print(f"Current Flow Rate: {flow_rate} L/min")

            if flow_rate > 0 and not flow_started:
                start_time = time.time()
                flow_started = True
                total_flow = 0.0

            if flow_started:
                elapsed_time = (time.time() - start_time) / 60.0
                total_flow += flow_rate * elapsed_time
                start_time = time.time()

            if flow_rate == 0 and flow_started:
                flow_started = False
                if total_flow > 0:
                    total_flow = round(total_flow, 2)
                    print(f"---------------Total consumed: {total_flow:.2f} liters---------------")
                    update_firebase(total_flow)
                    print("Consumption sent to Database")
                total_flow = 0.0

            last_flow_rate = flow_rate

        # Handle distance
        elif 'Distance:' in line:
            distance_str = line.split('Distance: ')[1].split(' cm')[0]
            distance = float(distance_str)
            print(f"Current Distance: {distance} cm")

            if (time.time() - distance_start_time) >= 300:
                send_distance_to_firebase(distance)
                distance_start_time = time.time()

            if last_flow_rate == 0 and (distance - last_distance) > 5:
                detect_leakage()

            last_distance = distance

        # Handle pH Value
        elif 'pH Value:' in line:
            ph_str = line.split('pH Value: ')[1].split(',')[0]
            voltage_str = line.split('Voltage: ')[1].split(' V')[0]
            ph_value = float(ph_str)
            ph_voltage = float(voltage_str)
            print(f"Current pH Value: {ph_value}, Voltage: {ph_voltage} V")

        # Handle Turbidity
        elif 'Turbidity:' in line:
            turbidity_str = line.split('Turbidity: ')[1].split(' NTU')[0]
            voltage_str = line.split('Voltage: ')[1].split(' V')[0]
            turbidity = float(turbidity_str)
            turbidity_voltage = float(voltage_str)
            print(f"Current Turbidity: {turbidity} NTU, Voltage: {turbidity_voltage} V")

    except (ValueError, IndexError):
        print("Received invalid data:", line)
