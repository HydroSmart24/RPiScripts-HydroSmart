import time
import random

def print_readings():
    distance_reading = 40  # Starting distance
    flow_rate = 0          # Constant flow rate

    while distance_reading <= 60:
        print(f"Distance reading: {distance_reading} cm")
        print(f"Water flow rate: {flow_rate} cm")
        distance = random.randint(1,3)
        distance_reading += distance
        sleep_time = random.randint(1, 5)  # Get a random sleep time between 1 and 5 seconds
        time.sleep(sleep_time)

if __name__ == "__main__":
    print_readings()
