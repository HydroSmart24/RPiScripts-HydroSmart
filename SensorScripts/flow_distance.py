import subprocess
import serial
import time
import os
import firebase_admin
from firebase_admin import credentials, firestore
import uuid  
from datetime import datetime

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

# Variables to track distance and pH/Turbidity values
initial_distance_at_zero_flow = None  
monitoring_for_leakage = False
last_distance = 0.0  
distance_start_time = time.time()
last_distance = 0.0
ph_values = []
turbidity_values = []
ph_start_time = time.time()

# Document ID and collection name for the relay state
document_id = 'DkIsHAZoGT5XIWKhTKd0'
collection_name = 'relayState'

# Initialize previous_relay_state with a default value
previous_relay_state = "OFF"  # Assuming relay starts in OFF state
current_relay_state = None

# Variable to track the last time the relay state changed
last_state_change_time = time.time()

# Function to update relay state in Firebase
def update_relay_state_in_firebase(state):
    try:
        # Get a reference to the specific document
        doc_ref = db.collection(collection_name).document(document_id)
        
        # Update the 'state' field with the new relay state
        doc_ref.update({'state': state})
        print(f"Successfully updated relay state to {state} in Firebase.")
    except Exception as e:
        print(f"Error updating relay state in Firebase: {e}")


# Function to handle relay state change with debounce logic
def handle_relay_state_change(new_state):
    global previous_relay_state, current_relay_state, last_state_change_time
    
    # Update current relay state
    current_relay_state = new_state
    
    # If the state changes from OFF to ON, send 'ON' to Firebase
    if previous_relay_state == "OFF" and current_relay_state == "ON":
        print("Relay state changed from OFF to ON. Sending 'ON' to Firebase...")
        update_relay_state_in_firebase("ON")

    # If the state changes from ON to OFF, send 'OFF' to Firebase
    elif previous_relay_state == "ON" and current_relay_state == "OFF":
        print("Relay state changed from ON to OFF. Sending 'OFF' to Firebase...")
        update_relay_state_in_firebase("OFF")
        
    # Update the last state change time
    last_state_change_time = time.time()
    
    # Update previous state for the next comparison
    previous_relay_state = current_relay_state


# Firebase update functions
def update_firebase(consumed_amount):
    doc_ref = db.collection('dailyConsumption').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'consumed_liters': round(consumed_amount, 2)  # Ensure the value is rounded to 2 decimal places
    })

def send_distance_to_firebase(distance):
    # Add new distance document
    doc_ref = db.collection('avgDistance').document()
    doc_ref.set({
        'time': firestore.SERVER_TIMESTAMP,
        'distance': round(distance, 2)
    })
    print(f"---------------Distance {distance:.2f} cm sent to Firebase---------------")

    # Keep only the latest 3 documents in the collection
    try:
        # Fetch all documents in the avgDistance collection, ordered by time
        docs = db.collection('avgDistance').order_by('time', direction=firestore.Query.DESCENDING).get()

        # If there are more than 3 documents, delete the oldest ones
        if len(docs) > 3:
            # Iterate over documents, starting from the 4th one (index 3)
            for doc in docs[3:]:
                print(f"Deleting old document: {doc.id}")
                db.collection('avgDistance').document(doc.id).delete()
        else:
            print("Less than or equal to 3 documents. No deletion required.")
    except Exception as e:
        print(f"Error cleaning up avgDistance collection: {e}")

def detect_leakage():
    # Add new leakage detection document
    doc_ref = db.collection('leakageDetect').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'status': 'detected'
    })
    print("---------------Leakage detected and reported---------------")

    # Keep only the latest 3 documents in the collection
    try:
        # Fetch all documents in the leakageDetect collection, ordered by timestamp
        docs = db.collection('leakageDetect').order_by('timestamp', direction=firestore.Query.DESCENDING).get()

        # If there are more than 3 documents, delete the oldest ones
        if len(docs) > 3:
            # Iterate over documents, starting from the 4th one (index 3)
            for doc in docs[3:]:
                print(f"Deleting old document: {doc.id}")
                db.collection('leakageDetect').document(doc.id).delete()
        else:
            print("Less than or equal to 3 documents. No deletion required.")
    except Exception as e:
        print(f"Error cleaning up leakageDetect collection: {e}")

def send_filter_health_to_firebase(avg_ph, avg_turbidity):
    doc_ref = db.collection('filterHealth').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'ph': round(avg_ph, 2),
        'turbidity': round(avg_turbidity, 2),
        'expirationDate': firestore.SERVER_TIMESTAMP
    })
    print(f"---------------Average pH {avg_ph:.2f}, Average Turbidity {avg_turbidity:.2f} sent to Firebase---------------")

    # Keep only the latest 3 documents in the collection
    try:
        # Fetch all documents in the filterHealth collection, ordered by timestamp
        docs = db.collection('filterHealth').order_by('timestamp', direction=firestore.Query.DESCENDING).get()

        # If there are more than 3 documents, delete the oldest ones
        if len(docs) > 3:
            # Iterate over documents, starting from the 4th one (index 3)
            for doc in docs[3:]:
                print(f"Deleting old document: {doc.id}")
                db.collection('filterHealth').document(doc.id).delete()
        else:
            print("Less than or equal to 3 documents. No deletion required.")
    except Exception as e:
        print(f"Error cleaning up filterHealth collection: {e}")

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

            # Handle leakage logic when flow rate is 0
            if flow_rate == 0 and not monitoring_for_leakage:                # Start monitoring for leakage when flow becomes zero
                initial_distance_at_zero_flow = last_distance
                monitoring_for_leakage = True
                print(f"Flow stopped. Monitoring for leakage with initial distance: {initial_distance_at_zero_flow:.2f} cm")

            last_flow_rate = flow_rate

        # Handle distance
        elif 'Distance:' in line:
            distance_str = line.split('Distance: ')[1].split(' cm')[0]
            distance = float(distance_str)
            print(f"Current Distance: {distance} cm")

            if (time.time() - distance_start_time) >= 120:  # 2 minutes
                send_distance_to_firebase(distance)
                distance_start_time = time.time()

            # Check for leakage when monitoring is active and flow is 0
            if monitoring_for_leakage and initial_distance_at_zero_flow is not None:
                if distance - initial_distance_at_zero_flow >= 2:
                    print(f"Distance increased by 2 cm. Detecting leakage...")
                    detect_leakage()
                    monitoring_for_leakage = False  # Stop monitoring after leakage is detected

            last_distance = distance

        # Handle pH Value
        elif 'pH Value:' in line:
            ph_str = line.split('pH Value: ')[1].split(',')[0]
            ph_value = float(ph_str)
            ph_values.append(ph_value)  # Collect pH values for averaging
            print(f"Current pH Value: {ph_value}")

        # Handle Turbidity
        elif 'Turbidity:' in line:
            turbidity_str = line.split('Turbidity: ')[1].split(' NTU')[0]
            turbidity = float(turbidity_str)

            # Cap the turbidity value at 10 NTU
            if turbidity > 10:
                turbidity = 10.0
            
            turbidity_values.append(turbidity)  # Collect capped turbidity values for averaging
            print(f"Current Turbidity: {turbidity} NTU")

        # Handle Relay State
        elif 'Relay State:' in line:
            relay_state = line.split('Relay State: ')[1]
            print(f"Relay State: {relay_state}")

            # Call the function to handle relay state change
            handle_relay_state_change(relay_state)

            print(f"-----------------------------------")

        # Check if 10 minutes have passed to send average pH and turbidity to Firebase
        if (time.time() - ph_start_time) >= 600:
            if ph_values and turbidity_values:
                avg_ph = sum(ph_values) / len(ph_values)
                avg_turbidity = (sum(turbidity_values) / len(turbidity_values)) - 4

                # Cap the average turbidity value at 10 before sending it to Firebase
                if avg_turbidity > 10:
                    avg_turbidity = 10.0

                send_filter_health_to_firebase(avg_ph, avg_turbidity)

            # Reset for the next 10 minutes
            ph_values.clear()
            turbidity_values.clear()
            ph_start_time = time.time()

    except (ValueError, IndexError):
        print("Received invalid data:", line)
