import os
import time

if __name__ == "__main__":
    while True:
        if not os.fork():
            os.execl("/usr/bin/python3.7", "/usr/bin/python3.7", "stats.py")
        time.sleep(1)
