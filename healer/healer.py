import os
import time
import urllib.request

import docker

TARGET_URL = os.getenv("TARGET_URL", "http://app:8000/health")
CONTAINER = os.getenv("TARGET_CONTAINER", "sentinelops-app")
INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))
THRESHOLD = int(os.getenv("FAIL_THRESHOLD", "3"))
COOLDOWN = int(os.getenv("COOLDOWN", "30"))

client = docker.from_env()


def log(message):
    print(f"[healer] {time.strftime('%H:%M:%S')} {message}", flush=True)


def is_healthy():
    try:
        with urllib.request.urlopen(TARGET_URL, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def restart():
    try:
        container = client.containers.get(CONTAINER)
        log(f"restarting {CONTAINER} (status: {container.status})")
        container.restart(timeout=10)
        log("restart issued")
    except Exception as error:
        log(f"restart failed: {error}")


def main():
    failures = 0
    log(f"watching {TARGET_URL}, restart after {THRESHOLD} failures")
    while True:
        if is_healthy():
            if failures:
                log("app is healthy again")
            failures = 0
        else:
            failures += 1
            log(f"health check failed ({failures}/{THRESHOLD})")
            if failures >= THRESHOLD:
                restart()
                failures = 0
                time.sleep(COOLDOWN)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()