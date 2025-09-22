import datetime

def log_action(action):
    """Log actions with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("access_log.txt", "a") as f:
        f.write(f"[{timestamp}] {action}\n")
