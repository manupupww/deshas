import sys
import subprocess

if __name__ == "__main__":
    print("Pradedamas kviesti Backend serverį (FastAPI)...")
    try:
        # Start uvicorn
        subprocess.check_call([sys.executable, "-m", "uvicorn", "backend.api:app", "--reload", "--host", "0.0.0.0", "--port", "8000"])
    except KeyboardInterrupt:
        print("\nSustabdoma.")
