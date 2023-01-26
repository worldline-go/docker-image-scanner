import time

class WaitNextProcess:
    def set_sleep_time(number, image_count):
        if image_count > 1:
            for intime in range(number, 0, -1):
                print(f"{intime} seconds remaining to trigger next process.")
                time.sleep(1)
