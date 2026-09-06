"""Log into the router and print the connected devices, over and over.

Step 2: watch whether devices appear and disappear steadily. Ctrl+C to stop.
"""

import hashlib
import os
import random
import time

import requests

ROUTER_IP = "192.168.31.1"

# The router's own MAC address, as reported by its newstatus reply. It goes
# into the nonce below. Not a secret.
ROUTER_MAC = "A4:39:B3:67:6D:21"

# Fixed string built into MiWiFi firmware, the same on every Xiaomi router.
# Not a secret either - it ships inside a JavaScript file anyone can download.
MIWIFI_SALT = "a2ffa5c9be07488bbb04a3a47d3c5f6a"

TIMEOUT = 10

# How long to wait between rounds. Turn it down while testing.
POLL_SECONDS = 3


def sha1(text):
    """Scramble text into a fixed-length value that cannot be reversed."""
    return hashlib.sha1(text.encode()).hexdigest()


def log_in(password):
    """Exchange the password for a short-lived token."""
    # A one-time string, so the proof below is never the same twice. Without it,
    # anyone who recorded one login could replay it forever.
    nonce = f"0_{ROUTER_MAC}_{int(time.time())}_{random.randint(1000, 10000)}"

    # Salt on the inside, nonce on the outside. The router runs the same sum
    # against the password it has stored; matching results prove we knew it.
    # The password itself never leaves this machine.
    proof = sha1(nonce + sha1(password + MIWIFI_SALT))

    reply = requests.post(
        f"http://{ROUTER_IP}/cgi-bin/luci/api/xqsystem/login",
        data={
            "username": "admin",
            "password": proof,
            "logtype": 2,
            "nonce": nonce,
        },
        timeout=TIMEOUT,
    ).json()

    if reply.get("code") != 0:
        raise SystemExit(f"The router refused the login: {reply}")

    # A short-lived pass. From here on the password is not needed again.
    return reply["token"]


password = os.environ.get("ROUTER_PASSWORD")
if not password:
    raise SystemExit(
        'ROUTER_PASSWORD is not set. In PowerShell:\n'
        '    $env:ROUTER_PASSWORD = "your router admin password"'
    )

try:
    token = log_in(password)
except requests.exceptions.RequestException as problem:
    # Can't reach the router at all on the way in. Stop, rather than pretend.
    raise SystemExit(f"Could not reach the router at {ROUTER_IP}: {problem}")

# What the last round saw, as MAC -> name. None means no round has happened
# yet. Only ever holds one round; nothing accumulates.
previous = None

while True:
    now = time.strftime("%H:%M:%S")

    try:
        devices_reply = requests.get(
            f"http://{ROUTER_IP}/cgi-bin/luci/;stok={token}/api/misystem/devicelist",
            timeout=TIMEOUT,
        ).json()

        if devices_reply.get("code") != 0:
            # Most likely the token expired. Get a new one, report next round.
            print(now, "token rejected, logging in again")
            token = log_in(password)
            time.sleep(POLL_SECONDS)
            continue

    except requests.exceptions.RequestException as problem:
        # We cannot tell who is home. Leave 'previous' untouched - treating a
        # failed round as an empty house would print a departure for everyone.
        print(now, "can't tell -", problem)
        time.sleep(POLL_SECONDS)
        continue

    # Identify devices by MAC, not name - names are not guaranteed unique.
    current = {}
    for device in devices_reply["list"]:
        current[device["mac"]] = device["name"]

    if previous is None:
        print(now, "watching:", ", ".join(current.values()))
    else:
        for mac in current:
            if mac not in previous:
                print(now, "ARRIVED", current[mac], mac)
        for mac in previous:
            if mac not in current:
                print(now, "LEFT   ", previous[mac], mac)

    previous = current
    time.sleep(POLL_SECONDS)
