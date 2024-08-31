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

def send_to_firebase(avg_distance):
    # Create a document in the 'avgDistance' collection
    doc_ref = db.collection('avgDistance').document()
    doc_ref.set({
        'time': firestore.SERVER_TIMESTAMP,  # Use server timestamp for accuracy
        'distance': avg_distance
    })
    print(f"Sent average distance {avg_distance:.2f} cm to Firebase")

# Variables for timing
start_time = time.time()
distance_readings = []

while True:
    line = ser.readline().decode('utf-8').strip()

    if 'Distance:' in line:
        try:
            # Extract distance
            distance_str = line.split('Distance: ')[1].split(' cm')[0]
            distance = float(distance_str)

            # Print the current distance reading every 10 seconds
            print(f"Current Distance: {distance} cm")
            distance_readings.append(distance)

            # Sleep for 10 seconds
            time.sleep(10)

            # Check if 5 minutes have passed
            if (time.time() - start_time) >= 300:
                if distance_readings:
                    # Calculate the average distance over the 5 minutes
                    avg_distance = sum(distance_readings) / len(distance_readings)

                    # Send the average distance to Firebase
                    send_to_firebase(avg_distance)

                    # Print log after sending to Firebase
                    print(f"Average distance of {avg_distance:.2f} cm sent to Firebase at {time.strftime('%Y-%m-%d %H:%M:%S')}")

                    # Reset the timer and readings list
                    start_time = time.time()
                    distance_readings = []

        except (ValueError, IndexError):
            print("Received invalid distance data:", line)
