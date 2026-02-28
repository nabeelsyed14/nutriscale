import random
import os
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()

# --- MOCK SERVICES ---

class MockScaleService:
    def __init__(self):
        self.last_weight = 0.0
        self.stable_counter = 0

    def get_weight(self):
        """
        Mock: Returns a stable weight that doesn't flicker wildly.
        Simulates 'placing' food (stays 0 for 3 calls, then hits 245.5g).
        """
        if self.stable_counter < 3:
            self.stable_counter += 1
            return 0.0
        
        if self.last_weight == 0.0:
            self.last_weight = round(float(random.uniform(150.0, 400.0)), 1)
        
        # Add tiny "noise" to look real, but not frustrating
        jitter = random.uniform(-0.1, 0.1)
        return round(float(self.last_weight + jitter), 1)

    def tare(self):
        """Mock tare."""
        print("[MOCK] Scale Tared.")
        self.stable_counter = 0
        self.last_weight = 0.0
        return True

class MockCameraService:
    def capture_image(self, save_path):
        """
        Mock: Creates a dummy image file at the specified path.
        """
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            from PIL import Image
            img = Image.new('RGB', (640, 480), color = (73, 109, 137))
            img.save(save_path)
            return True
        except ImportError:
            with open(save_path, 'wb') as f:
                f.write(b'fake image data')
            return True



# --- REAL HARDWARE SERVICES (Raspberry Pi) ---

class RealScaleService:
    def __init__(self):
        self.scale_lock = threading.Lock()
        print("[HARDWARE] Initializing Pi 5 Scale (GPIOZero)...")
        try:
            from gpiozero import DigitalInputDevice, DigitalOutputDevice
            # PIN CONFIG (BCM)
            self.dout = DigitalInputDevice(5)
            self.pd_sck = DigitalOutputDevice(6)
            self.pd_sck.off()
            
            # Calibration state
            self.offset = 0
            self.reference_unit = float(os.getenv("SCALE_REFERENCE_UNIT", "1.0"))
            
            # Wait for hardware to stabilize
            time.sleep(0.5)
            
            # Initial Tare
            self.tare()
        except Exception as e:
            print(f"[HARDWARE] Scale failed: {e}")
            self.dout = None

    def _get_raw(self):
        if not self.dout: return None
        # Wait for ready (max 1.0s as per v1 stable)
        start = time.time()
        while self.dout.value == 1:
            if time.time() - start > 1.0: 
                return None
        
        # Read 24 bits
        raw = 0
        for _ in range(24):
            self.pd_sck.on()
            raw = (raw << 1) | self.dout.value
            self.pd_sck.off()
        
        # 1 pulse for GAIN=128
        self.pd_sck.on()
        self.pd_sck.off()
        
        # 2's complement
        if raw & 0x800000: raw -= 0x1000000
        return raw

    def get_weight(self):
        if not self.dout: return 0.0
        locked = self.scale_lock.acquire(blocking=False)
        if not locked: return 0.0
        
        try:
            samples = []
            # High-sample count (15) for high accuracy
            for _ in range(15):
                val = self._get_raw()
                if val is not None and val != 0 and val != -1:
                    samples.append(val)
                time.sleep(0.001) 
            
            if len(samples) < 5: return 0.0
            
            # STABILITY WIN: Sort and trim top/bottom outliers (Median-Hybrid)
            samples.sort()
            trimmed = samples[3:-3] # Remove 3 lowest and 3 highest
            if not trimmed: trimmed = samples
            
            avg_raw = sum(trimmed) / len(trimmed)
            weight = (avg_raw - self.offset) / self.reference_unit
            
            # Noise Floor: Ignore jitter under 1.0g
            if abs(weight) < 1.0: return 0.0
            
            return round(weight, 1)
        except Exception as e: 
            print(f"[HARDWARE] Scale error: {e}")
            return 0.0
        finally:
            self.scale_lock.release()

    def tare(self):
        """Zero out the scale (with locking)."""
        with self.scale_lock:
            print("[HARDWARE] Taring scale...")
            samples = []
            for _ in range(30):
                val = self._get_raw()
                if val is not None:
                    samples.append(val)
                time.sleep(0.001)
            if len(samples) > 10:
                samples.sort()
                trimmed = samples[5:-5]
                self.offset = sum(trimmed) / len(trimmed)
                print(f"[HARDWARE] Scale Ready. Initial Offset: {self.offset:.2f}")
                return True
            print("[HARDWARE] Tare Failed: No stable data.")
            return False

import threading

class RealCameraService:
    def __init__(self):
        self.camera_lock = threading.Lock()
        self.latest_frame = None
        self.binaries = self._discover_binaries()
        print(f"[HARDWARE] Real Camera Service Initialized. Binaries found: {self.binaries}")

    def _discover_binaries(self):
        import shutil
        tools = {
            "still": ["rpicam-still", "rpicam-jpeg", "libcamera-still", "libcamera-jpeg"],
            "vid": ["rpicam-vid", "libcamera-vid"]
        }
        found = {"still": None, "vid": None}
        for category, options in tools.items():
            for opt in options:
                path = shutil.which(opt)
                if path:
                    found[category] = opt
                    break
        return found

    def capture_image(self, save_path):
        """Captures image by snapping the latest frame from stream (avoiding busy hardware)."""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # If we have a live frame in memory, use it! (Avoids "Camera Busy" errors)
        if self.latest_frame:
            try:
                with open(save_path, 'wb') as f:
                    f.write(self.latest_frame)
                print(f"[HARDWARE] Image Snapped from Stream: {save_path}")
                return True
            except Exception as e:
                print(f"[HARDWARE] Failed to save snapped frame: {e}")

        # Fallback: Try a full high-res capture ONLY if stream is not running
        cmd_base = self.binaries.get("still")
        if not cmd_base:
            print("[HARDWARE] ERROR: No capture binary found.")
            return False

        with self.camera_lock:
            cmd = [cmd_base, "-o", save_path, "-t", "500", "--width", "1920", "--height", "1440", "--nopreview"]
            try:
                print(f"[HARDWARE] Attempting full cap (Fallback): {' '.join(cmd)}")
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                if os.path.exists(save_path): 
                    print(f"[HARDWARE] Capture Success: {save_path}")
                    return True
            except Exception as e:
                print(f"[HARDWARE] Full capture failed (likely busy): {e}")
        return False

    def gen_frames(self):
        """Continuous MJPEG stream using discovered vid binary."""
        cmd_base = self.binaries.get("vid")
        if not cmd_base:
            print("[HARDWARE] ERROR: No video binary found (rpicam-vid or libcamera-vid)")
            return

        # Pi 5 Tuned MJPEG Stream
        cmd = [
            cmd_base, "-t", "0", 
            "--codec", "mjpeg", 
            "--inline", # Critical for MJPEG frame boundaries
            "--width", "640", "--height", "480", 
            "--framerate", "10", # Slower framerate = less network/CPU jitter
            "--nopreview", 
            "--denoise", "cdn_off", 
            "--flush", # Ensure frames aren't buffered in the pipe
            "-o", "-"
        ]
        
        print(f"[HARDWARE] Starting Video Stream: {' '.join(cmd)}")
        
        process = None
        try:
            # bufsize=0 is critical for streaming pipes
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            
            buffer = b""
            last_frame_time = time.time()
            
            while True:
                # 1. Monitor process health
                if process.poll() is not None:
                    err = process.stderr.read().decode()
                    print(f"[HARDWARE] Camera process exited unexpectedly. Stderr: {err}")
                    break

                # 2. Read with timeout-like behavior
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                
                buffer += chunk
                
                # 3. Extract MJPEG frames
                while b'\xff\xd8' in buffer and b'\xff\xd9' in buffer:
                    start = buffer.find(b'\xff\xd8')
                    end = buffer.find(b'\xff\xd9', start)
                    
                    if start != -1 and end != -1:
                        jpg = buffer[start:end+2]
                        buffer = buffer[end+2:]
                        
                        # Store as the latest snap-able frame
                        self.latest_frame = jpg
                        
                        last_frame_time = time.time()

                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
                    else:
                        break
                
                if len(buffer) > 1000000:
                    buffer = b""

        except Exception as e:
            print(f"[HARDWARE] Stream Error: {e}")
        finally:
            if process:
                print("[HARDWARE] Cleaning up camera process...")
                process.terminate()
                try: process.wait(timeout=0.5)
                except: process.kill()


# --- SMART FACTORY ---

def get_services():
    use_real = os.getenv("USE_REAL_HARDWARE", "false").lower() == "true"
    
    if not use_real:
        print(">>> STARTING IN MOCK HARDWARE MODE <<<")
        return MockScaleService(), MockCameraService()

    print(">>> STARTING IN SMART HARDWARE MODE (Real where possible) <<<")
    
    # 1. Scale
    try:
        scale = RealScaleService()
        if scale.dout is None: raise Exception("HX711 not found")
        print("[HARDWARE] Scale: REAL")
    except:
        scale = MockScaleService()
        print("[HARDWARE] Scale: MOCK (Hardware not detected)")

    # 2. Camera
    camera = RealCameraService()
    print("[HARDWARE] Camera: REAL")

    return scale, camera

# Export singleton instances
scale_service, camera_service = get_services()
