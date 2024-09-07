import subprocess
import serial
import time
import os
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid  
from datetime import datetime

# Path to the Firebase service account JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), '..', 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'rpiwaterconsumption.appspot.com'
})

db = firestore.client()
bucket = storage.bucket()

# Open serial port
ser = serial.Serial('/dev/ttyACM0', 9600)  # Adjust the port and baud rate as needed

# Variables to track flow and time
flow_started = False
start_time = 0
total_flow = 0.0
last_flow_rate = 0.0

# Variables to track distance and pH/Turbidity values
distance_start_time = time.time()
last_distance = 0.0
ph_values = []
turbidity_values = []
ph_start_time = time.time()

def generate_unique_filename(base_name):
    """Generate a unique filename by appending a UUID to the base name."""
    name, ext = os.path.splitext(base_name)
    unique_name = f"{name}_{uuid.uuid4().hex}{ext}"
    return unique_name


def capture_image(image_path="output_image.jpg", retries=10, delay=2):
    command = [
        "ffmpeg", "-f", "v4l2", "-input_format", "mjpeg", "-video_size", "640x480",
        "-i", "/dev/video0", "-vf", "format=yuv420p", "-vframes", "1", image_path
    ]
    
    attempt = 0
    while attempt < retries:
        try:
            # Add a delay before each retry to ensure the camera is ready
            time.sleep(delay)
            subprocess.run(command, check=True)
            print(f"Image captured successfully: {image_path}")
            return True
        except subprocess.CalledProcessError:
            attempt += 1
            print(f"Failed to capture image on attempt {attempt}. Retrying...")
    
    print("Failed to capture image after all retries.")
    return False


def upload_to_firebase(image_path):
    try:
        # Get the current timestamp
        timestamp = datetime.utcnow().isoformat()

        # Upload the image file to Firebase Storage with metadata
        blob = bucket.blob(f'images/{os.path.basename(image_path)}')
        metadata = {"timestamp": timestamp}  # Add metadata with timestamp
        blob.upload_from_filename(image_path, content_type='image/jpeg')
        blob.metadata = metadata
        blob.patch()  # Apply the metadata

        blob.make_public()  # Optional: Make the file publicly accessible

        # Get the public URL of the image
        image_url = blob.public_url
        print(f"Image uploaded to Firebase Storage: {image_url}")

        # Store the image URL and metadata in Firestore
        document_id = os.path.splitext(os.path.basename(image_path))[0]
        doc_ref = db.collection('images').document(document_id)
        doc_ref.set({
            'image_url': image_url,
            'timestamp': timestamp  # Save the timestamp in Firestore
        })

        print(f"Image URL and metadata uploaded to Firestore: {image_url}")
    except Exception as e:
        print(f"Failed to upload image to Firebase: {e}")



# Initialize previous_relay_state with a default value
previous_relay_state = "OFF"  # Assuming relay starts in OFF state
current_relay_state = None

# Variable to track the last time the relay state changed
last_state_change_time = time.time()

# Function to handle relay state change with debounce logic
def handle_relay_state_change(new_state):
    global previous_relay_state, current_relay_state, last_state_change_time
    
    # Update current relay state
    current_relay_state = new_state
    
    # Check if the state changed from 'ON' to 'OFF'
    if previous_relay_state == "ON" and current_relay_state == "OFF":
        
        # Ensure the state has remained OFF for at least 1 second (debounce logic)
        current_time = time.time()
        if current_time - last_state_change_time >= 1:  # 1 second debounce
            print("Relay state changed from ON to OFF. Triggering image capture and upload.")
            
            # Generate a unique filename before capturing the image
            image_path = generate_unique_filename("output_image.jpg")
            
            # Capture and upload the image
            if capture_image(image_path):
                upload_to_firebase(image_path)
            
            # Update the last state change time
            last_state_change_time = current_time
    
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

def send_filter_health_to_firebase(avg_ph, avg_turbidity):
    doc_ref = db.collection('filterHealth').document()
    doc_ref.set({
        'timestamp': firestore.SERVER_TIMESTAMP,
        'ph': round(avg_ph, 2),
        'turbidity': round(avg_turbidity, 2),
        'expirationDate': firestore.SERVER_TIMESTAMP
    })
    print(f"---------------Average pH {avg_ph:.2f}, Average Turbidity {avg_turbidity:.2f} sent to Firebase---------------")

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
            ph_value = float(ph_str)
            ph_values.append(ph_value)  # Collect pH values for averaging
            print(f"Current pH Value: {ph_value}")

        # Handle Turbidity
        elif 'Turbidity:' in line:
            turbidity_str = line.split('Turbidity: ')[1].split(' NTU')[0]
            turbidity = float(turbidity_str)
            turbidity_values.append(turbidity)  # Collect turbidity values for averaging
            print(f"Current Turbidity: {turbidity} NTU")

        # Handle Relay State
        elif 'Relay State:' in line:
            relay_state = line.split('Relay State: ')[1]
            print(f"Relay State: {relay_state}")

            # Trigger image capture when relay state changes from ON to OFF
            handle_relay_state_change(relay_state)

            print(f"-----------------------------------")

        # Check if 10 minutes have passed to send average pH and turbidity to Firebase
        if (time.time() - ph_start_time) >= 600:
            if ph_values and turbidity_values:
                avg_ph = sum(ph_values) / len(ph_values)
                avg_turbidity = sum(turbidity_values) / len(turbidity_values)
                send_filter_health_to_firebase(avg_ph, avg_turbidity)

            # Reset for the next 10 minutes
            ph_values.clear()
            turbidity_values.clear()
            ph_start_time = time.time()

    except (ValueError, IndexError):
        print("Received invalid data:", line)
