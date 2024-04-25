import RPi.GPIO as GPIO
import time

# Set GPIO mode (BCM mode)
GPIO.setmode(GPIO.BCM)

# Define GPIO pins for trigger and echo
TRIG = 23
ECHO = 24

# Set up GPIO pins
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance():
    # Set trigger to HIGH for 10 microseconds
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    start_time = time.time()
    stop_time = time.time()

    # Save start time
    while GPIO.input(ECHO) == 0:
        start_time = time.time()

    # Save stop time
    while GPIO.input(ECHO) == 1:
        stop_time = time.time()

    # Calculate elapsed time
    elapsed_time = stop_time - start_time

    # Calculate distance (in cm)
    distance = (elapsed_time * 34300) / 2

    return distance

try:
    while True:
        # Get distance
        dist = get_distance()
        print("Distance: {:.2f} cm".format(dist))
        time.sleep(10)  # Print the reading every 10 seconds

except KeyboardInterrupt:
    # Clean up GPIO
    GPIO.cleanup()

    #Updated code for CICD

    #Write a seperate function to get the daily consumption 