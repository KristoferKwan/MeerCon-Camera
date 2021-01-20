from gpiozero import MotionSensor
from gpiozero import LED
import record_video
import time
import threading
from datetime import datetime
import RPi.GPIO as GPIO

def get_filename():
    filename = str(datetime.now()).replace(" ", "_")
    return f"./videos/{filename}.mp4"

def now():
    return time.asctime(time.localtime(time.time()))

GPIO.setmode(GPIO.BCM)
pir = MotionSensor(17)
green_led = LED(16)
green_led.off()
print("starting scan")
end_time = time.time()
 
 
time.sleep(2)
while True:
    try:
        pir.wait_for_motion()
        start_time = time.time()
        print(f"Motion detected!: {start_time - end_time} seconds since motion not detected\n\ttime: {now()}")
        green_led.on()
        record_video.start_recording(filename=get_filename())
        time.sleep(5)
        green_led.off()
        end_time = time.time()
        time.sleep(0.1)
    except KeyboardInterrupt:
        print("gracefully shutting down")
        break

