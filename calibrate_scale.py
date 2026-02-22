import os
import time
import sys

# Try to import gpiozero (will be installed by setup_pi.sh)
try:
    from gpiozero import DigitalInputDevice, DigitalOutputDevice
except ImportError:
    print("ERROR: gpiozero not found. Please run ./setup_pi.sh first.")
    sys.exit(1)

class HX711_Pi5:
    """
    A simple Pi 5 compatible HX711 bit-banging class using gpiozero.
    """
    def __init__(self, dout_pin, pd_sck_pin, gain=128):
        self.pd_sck = DigitalOutputDevice(pd_sck_pin)
        self.dout = DigitalInputDevice(dout_pin)
        self.gain = 128
        self.offset = 0
        self.reference_unit = 1
        
        self.pd_sck.off()
        self.set_gain(gain)

    def set_gain(self, gain):
        if gain == 128: self.gain_pulses = 1
        elif gain == 64: self.gain_pulses = 3
        elif gain == 32: self.gain_pulses = 2
        else: self.gain_pulses = 1 # Default 128
        
        # Reset HX711
        self.pd_sck.on()
        time.sleep(0.0001)
        self.pd_sck.off()
        self.get_raw()

    def is_ready(self):
        return self.dout.value == 0

    def get_raw(self):
        # Wait for ready
        timeout = 2.0
        start = time.time()
        while not self.is_ready():
            if time.time() - start > timeout:
                return None
        
        # Read 24 bits
        raw_data = 0
        for _ in range(24):
            self.pd_sck.on()
            # No sleep needed for Pi 5 speed usually, but tiny delay for safety
            raw_data = (raw_data << 1) | self.dout.value
            self.pd_sck.off()
            
        # Gain pulses (1, 2, or 3)
        for _ in range(self.gain_pulses):
            self.pd_sck.on()
            self.pd_sck.off()
            
        # Convert 2's complement
        if raw_data & 0x800000:
            raw_data -= 0x1000000
            
        return raw_data

    def get_value(self, samples=10):
        total = 0
        count = 0
        for _ in range(samples):
            val = self.get_raw()
            if val is not None:
                total += val
                count += 1
            time.sleep(0.01)
        
        if count == 0: return 0
        return total / count

    def tare(self, samples=15):
        print("Taring... stay still.")
        self.offset = self.get_value(samples)
        print(f"Tare complete. Offset: {self.offset}")

    def get_weight(self, samples=10):
        val = self.get_value(samples) - self.offset
        return val / self.reference_unit

def run_calibration():
    # PIN CONFIG (BCM numbering)
    DOUT = 5
    SCK = 6
    
    print("--- NutriScale Load Cell Calibration (Pi 5) ---")
    print(f"Using Pins: DOUT={DOUT}, SCK={SCK}")
    
    try:
        hx = HX711_Pi5(DOUT, SCK)
    except Exception as e:
        print(f"FAILED to initialize GPIO: {e}")
        return

    print("\n1. Remove everything from the scale.")
    input("Press Enter to Tare...")
    hx.tare()
    
    print("\n2. Place a KNOWN weight on the scale (e.g., a 100g phone or weight).")
    known_weight = input("Enter the weight in grams: ")
    try:
        known_weight = float(known_weight)
    except:
        print("Invalid input.")
        return
        
    print(f"Reading {known_weight}g...")
    raw_value = hx.get_value(20) - hx.offset
    
    if raw_value == 0:
        print("ERROR: Raw value is 0. Is the HX711 connected correctly?")
        return
        
    ref_unit = raw_value / known_weight
    print("\n" + "="*40)
    print(f"CALIBRATION SUCCESS!")
    print(f"Your Reference Unit is: {ref_unit}")
    print("="*40)
    print(f"\nAdd this line to your .env file on the Pi:")
    print(f"SCALE_REFERENCE_UNIT={ref_unit}")
    print("="*40)

if __name__ == "__main__":
    run_calibration()
