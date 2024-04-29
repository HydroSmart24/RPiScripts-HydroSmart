import RPi.GPIO as GPIO
import time
import firebase_admin
from firebase_admin import credentials, firestore 
import os

# Path to the Firebase service acccount JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Set GPIO mode (BCM mode)
GPIO.setmode(GPIO.BCM)

# Define GPIO pins for trigger and echo
TRIG = 23
ECHO = 24

# Set up GPIO pins
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start_time = time.time()
    stop_time = time.time()

    while GPIO.input(ECHO) == 0:
        start_time = time.time()

    while GPIO.input(ECHO) == 1:
        stop_time = time.time()

    elapsed_time = stop_time - start_time

    # Calculate distance (in cm)
    distance = (elapsed_time * 34300) / 2

    return distance

def event_trigger(threshold_distance):
   
    last_distance = None

    try:
        while True:
         
            current_distance = get_distance()

            if last_distance is None:
                last_distance = current_distance
                continue  

            distance_difference = abs(current_distance - last_distance)

            if distance_difference <= threshold_distance:
                continue

            print("Distance changed by {:.2f} cm".format(distance_difference))
            last_distance = current_distance
            time.sleep(1)  

    except KeyboardInterrupt:
        # Clean up GPIO
        GPIO.cleanup()

# Define threshold distance for event triggering
threshold_distance = 45.0  

event_trigger(threshold_distance)