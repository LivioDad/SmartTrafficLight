from gpiozero import LED
import time

# Define the LEDs on pins 5, 6, 7, and 8
ledg1 = LED(5)  # Green LED 1 (pin 5)
ledr1 = LED(6)  # Red LED 1 (pin 6)
ledg2 = LED(8)  # Green LED 2 (pin 8)
ledr2 = LED(7)  # Red LED 2 (pin 7)

wait = 0.1

while True:
    # Turn on red LED 2 and turn off all others
    ledr2.on()
    ledg2.off()
    ledr1.off()
    ledg1.off()
    print("r2 on, others off")
    
    time.sleep(wait)
    
    # Turn on green LED 2 and turn off all others
    ledr2.off()
    ledg2.on()
    ledr1.off()
    ledg1.off()
    print("g2 on, others off")
    
    # Wait for 0.5 second
    time.sleep(wait)
    
    # Turn on red LED 1 and turn off all others
    ledr2.off()
    ledg2.off()
    ledr1.on()
    ledg1.off()
    print("r1 on, others off")
    
    # Wait for 0.5 second
    time.sleep(wait)
    
    # Turn on green LED 1 and turn off all others
    ledr2.off()
    ledg2.off()
    ledr1.off()
    ledg1.on()
    print("g1 on, others off")
    
    # Wait for 0.5 second
    time.sleep(wait)
