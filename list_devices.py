"""Log into the router and print the list of connected devices."""

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


def sha1(text):
    """Scramble text into a fixed-length value that cannot be reversed."""
    return hashlib.sha1(text.encode()).hexdigest()


password = os.environ.get("ROUTER_PASSWORD")
if not password:
    raise SystemExit(
        'ROUTER_PASSWORD is not set. In PowerShell:\n'
        '    $env:ROUTER_PASSWORD = "your router admin password"'
    )

# A one-time string, so the proof below is never the same twice. Without it,
# anyone who recorded one login could replay it forever.
nonce = f"0_{ROUTER_MAC}_{int(time.time())}_{random.randint(1000, 10000)}"

# Salt on the inside, nonce on the outside. The router runs the same sum
# against the password it has stored; matching results prove we knew it.
# The password itself never leaves this machine.
proof = sha1(nonce + sha1(password + MIWIFI_SALT))

try:
    login_reply = requests.post(
        f"http://{ROUTER_IP}/cgi-bin/luci/api/xqsystem/login",
        data={
            "username": "admin",
            "password": proof,
            "logtype": 2,
            "nonce": nonce,
        },
        timeout=TIMEOUT,
    ).json()

    if login_reply.get("code") != 0:
        raise SystemExit(f"The router refused the login: {login_reply}")

    # A short-lived pass. From here on the password is not needed again.
    token = login_reply["token"]

    devices_reply = requests.get(
        f"http://{ROUTER_IP}/cgi-bin/luci/;stok={token}/api/misystem/devicelist",
        timeout=TIMEOUT,
    ).json()

    if devices_reply.get("code") != 0:
        raise SystemExit(f"The router would not give the device list: {devices_reply}")

except requests.exceptions.RequestException as problem:
    # Reaching the router failed outright. Say so - never fall through to an
    # empty list, which would read as "nobody is home".
    raise SystemExit(f"Could not reach the router at {ROUTER_IP}: {problem}")

for device in devices_reply["list"]:
    # 'ip' is a list, because a device can hold more than one address.
    address = device["ip"][0]["ip"]
    print(device["name"], address, device["mac"])
