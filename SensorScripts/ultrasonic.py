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

def event_trigger(threshold_distance):
    """
    Implement event-based trigger system.
    """
    last_distance = None

    try:
        while True:
            # Get current distance
            current_distance = get_distance()

            # Check if last_distance is None
            if last_distance is None:
                last_distance = current_distance
                continue  # Skip comparison in the first iteration

            # Calculate the difference in distance
            distance_difference = abs(current_distance - last_distance)

            # If the difference is less than or equal to 45.00 cm, continue to the next iteration
            if distance_difference <= threshold_distance:
                continue

            # Otherwise, print the actual difference
            print("Distance changed by {:.2f} cm".format(distance_difference))
            
            last_distance = current_distance

            # Sleep for a short interval before taking the next measurement
            time.sleep(1)  # Adjust as needed

    except KeyboardInterrupt:
        # Clean up GPIO
        GPIO.cleanup()

# Define threshold distance for event triggering
threshold_distance = 45.0  # Adjust as needed

# Start event trigger system
event_trigger(threshold_distance)

#test CICD