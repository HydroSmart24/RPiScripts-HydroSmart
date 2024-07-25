import time

def print_readings():
    distance_reading = 40  # Starting distance
    flow_rate = 0          # Constant flow rate

    while distance_reading <= 60:
        print(f"Distance reading: {distance_reading} cm")
        print(f"Water flow rate: {flow_rate} cm")
        distance_reading += 2
        time.sleep(3)  # Wait for 1 second before the next reading

if __name__ == "__main__":
    print_readings()
