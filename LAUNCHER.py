import subprocess
import time
import threading

# Set this to False to skip simulators
USE_SIMULATORS = True

# List of essential scripts
scripts = [
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/database_adaptor/database_adaptor.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/resource_catalog/resource_catalog_server.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/LedManager/led_manager.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Lights/LED_light1.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Lights/LED_light2.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/LCD/LCD_screen_script.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/LCD/services/road_ice_prediction.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/DHT22.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/DHT11.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/PIR.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/Button.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/HC_SR04_distance.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/ThingSpeak_Adaptor.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/infraction_sensor.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/telegram_bot/telegram_bot.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/violation_detection/violation_detection.py",
]

# Optional simulators
simulators = [
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/LCD/services/ice_risk_sim.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/scripts/Sensors/INFRACTION_SIMULATOR.py",
    "/home/liviodad/Desktop/virtualenv/SmartTrafficLight/LedManager/emergency_sim.py",
]

# Store subprocesses
processes = []

def launch_all():
    to_run = scripts + (simulators if USE_SIMULATORS else [])
    for script in to_run:
        print(f"Launching {script}...")
        p = subprocess.Popen(["python3", script])
        processes.append(p)
        time.sleep(3)
    print("All scripts launched.\nType 'stop' to terminate them all.")

def wait_for_stop_command():
    while True:
        cmd = input()
        if cmd.strip().lower() == "stop":
            print("\nStopping all scripts...")
            for p in processes:
                p.terminate()
            for p in processes:
                p.wait()
            print("All scripts stopped.")
            break

if __name__ == "__main__":
    launcher_thread = threading.Thread(target=launch_all)
    stopper_thread = threading.Thread(target=wait_for_stop_command)

    launcher_thread.start()
    stopper_thread.start()

    launcher_thread.join()
    stopper_thread.join()