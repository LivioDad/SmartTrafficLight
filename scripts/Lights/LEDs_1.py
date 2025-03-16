from gpiozero import LED
import time

ledG_NS = LED(6)  # Green LED for North-South
ledR_NS = LED(5)  # Red LED for North-South
ledR_WE = LED(8)  # Red LED for West-East
ledG_WE = LED(7)  # Green LED for West-East

wait = 0.1

for i in range(3):
    # Turn on red LED for West-East and turn off all others
    ledR_WE.on()
    ledG_WE.off()
    ledR_NS.off()
    ledG_NS.off()
    print("Red WE on, others off")
    
    time.sleep(wait)
    
    # Turn on green LED for West-East and turn off all others
    ledR_WE.off()
    ledG_WE.on()
    ledR_NS.off()
    ledG_NS.off()
    print("Green WE on, others off")
    
    time.sleep(wait)
    
    # Turn on red LED for North-South and turn off all others
    ledR_WE.off()
    ledG_WE.off()
    ledR_NS.on()
    ledG_NS.off()
    print("Red NS on, others off")
    
    time.sleep(wait)
    
    # Turn on green LED for North-South and turn off all others
    ledR_WE.off()
    ledG_WE.off()
    ledR_NS.off()
    ledG_NS.on()
    print("Green NS on, others off")
    
    time.sleep(wait)

ledG_NS = LED(21)  # Green LED for North-South
ledR_NS = LED(20)  # Red LED for North-South
ledR_WE = LED(12)  # Red LED for West-East
ledG_WE = LED(16)  # Green LED for West-East

for i in range(3):
    # Turn on red LED for West-East and turn off all others
    ledR_WE.on()
    ledG_WE.off()
    ledR_NS.off()
    ledG_NS.off()
    print("Red WE on, others off")
    
    time.sleep(wait)
    
    # Turn on green LED for West-East and turn off all others
    ledR_WE.off()
    ledG_WE.on()
    ledR_NS.off()
    ledG_NS.off()
    print("Green WE on, others off")
    
    time.sleep(wait)
    
    # Turn on red LED for North-South and turn off all others
    ledR_WE.off()
    ledG_WE.off()
    ledR_NS.on()
    ledG_NS.off()
    print("Red NS on, others off")
    
    time.sleep(wait)
    
    # Turn on green LED for North-South and turn off all others
    ledR_WE.off()
    ledG_WE.off()
    ledR_NS.off()
    ledG_NS.on()
    print("Green NS on, others off")
    
    time.sleep(wait)