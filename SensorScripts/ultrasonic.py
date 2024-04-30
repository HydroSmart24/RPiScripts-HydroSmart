import RPi.GPIO as GPIO
import time
import firebase_admin
from firebase_admin import credentials, firestore 
import os
from distance_util import get_most_common_distances

# Path to the Firebase service acccount JSON file
firebase_credentials_file = os.path.join(os.path.dirname(__file__), '..', 'Firebase', 'serviceAccountKey.json')

# Initialize Firebase Admin SDK with service account credentials
cred = credentials.Certificate(firebase_credentials_file)
firebase_admin.initialize_app(cred)
db = firestore.client()


GPIO.setmode(GPIO.BCM)

TRIG = 23
ECHO = 24

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    # Set trigger to HIGH for 10 microseconds
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

    distance = int((elapsed_time * 34300) / 2)

    return distance

def event_trigger(threshold_distance):
    last_distance = None
    distance_list = []
    start_time = time.time()

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
            distance_list.append(distance_difference)
            last_distance = current_distance

            time.sleep(5)  

            elapsed_time = time.time() - start_time
            if elapsed_time >= 180:  # 180 seconds = 3 minutes
                avg_distance = get_most_common_distances(distance_list)
                print("Average of the 3 most common distances: {:.2f} cm".format(avg_distance))
                distance_list.clear()
                start_time = time.time()

    except KeyboardInterrupt:
        GPIO.cleanup()


threshold_distance = 45.0


event_trigger(threshold_distance)
