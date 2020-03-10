import os
import time

if __name__ == "__main__":
    while True:
        if not os.fork():
            os.execl("stats.py", "stats.py")
        time.sleep(1)
