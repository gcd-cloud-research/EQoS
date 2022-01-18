import os
import time

if __name__ == "__main__":
    while True:
        if not os.fork():
            os.execlp("python3.7", "python3.7", "stats.py")
        time.sleep(1)
