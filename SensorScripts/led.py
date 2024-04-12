from gpiozero import LED
from time import sleep

# Define the GPIO pin connected to your LED
# Adjust the pin number as per your setup
led_pin = 22  # Example GPIO pin, change as needed

# Initialize the LED object
led = LED(led_pin)

try:
    while True:
        # Turn the LED on
        led.on()
        print("LED on")
        
        # Wait for 1 second
        sleep(1)
        
        # Turn the LED off
        led.off()
        print("LED off")
        
        # Wait for 4 seconds (total cycle time is 5 seconds)
        sleep(2)

except KeyboardInterrupt:
    # Clean up GPIO on Ctrl+C exit
    led.off()
