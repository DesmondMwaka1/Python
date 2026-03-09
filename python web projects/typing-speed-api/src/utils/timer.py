def start_timer():
    import time
    return time.time()

def stop_timer(start_time):
    import time
    return time.time() - start_time