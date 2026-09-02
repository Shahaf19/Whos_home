"""Print the devices currently connected to the Xiaomi router.

Step 1 of the presence tracker: just prove we can get the list at all.
Run it with the router's admin password in the environment:

    export ROUTER_PASSWORD="..."      # bash
    $env:ROUTER_PASSWORD = "..."      # PowerShell
    python list_devices.py
"""

import hashlib
import os
import random
import sys
import time

import requests

ROUTER_IP = "192.168.31.1"
ROUTER_MAC = "c8:bf:4c:71:b7:44"

# Fixed salt baked into MiWiFi firmware. Not a secret - it's the same on every
# Xiaomi router, and the login hash below is built from it.
MIWIFI_SALT = "a2ffa5c9be07488bbb04a3a47d3c5f6a"

TIMEOUT = 10


def sha1(text):
    return hashlib.sha1(text.encode()).hexdigest()


def log_in(password):
    """Exchange the password for a short-lived session token (the 'stok')."""
    # A one-time string, so the same scramble is never sent twice.
    nonce = f"0_{ROUTER_MAC}_{int(time.time())}_{random.randint(1000, 10000)}"

    # Scramble password and nonce together. The router does the same sum with
    # the password it has stored; matching results prove we knew it.
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
        raise SystemExit(f"Login refused by the router: {reply}")

    return reply["token"]


def get_devices(token):
    reply = requests.get(
        f"http://{ROUTER_IP}/cgi-bin/luci/;stok={token}/api/misystem/devicelist",
        timeout=TIMEOUT,
    ).json()

    if reply.get("code") != 0:
        raise SystemExit(f"Router would not give the device list: {reply}")

    return reply.get("list", [])


def main():
    password = os.environ.get("ROUTER_PASSWORD")
    if not password:
        raise SystemExit(
            'ROUTER_PASSWORD is not set. In PowerShell:\n'
            '    $env:ROUTER_PASSWORD = "your router admin password"'
        )

    try:
        token = log_in(password)
        devices = get_devices(token)
    except requests.exceptions.RequestException as problem:
        raise SystemExit(f"Could not reach the router at {ROUTER_IP}: {problem}")

    print(f"{'NAME':<28} {'IP':<16} MAC")
    for device in devices:
        # 'ip' is a list because a device can hold more than one address.
        addresses = device.get("ip") or [{}]
        ip = addresses[0].get("ip", "-")
        print(f"{device.get('name', '?'):<28} {ip:<16} {device.get('mac', '?')}")

    print(f"\n{len(devices)} devices")


if __name__ == "__main__":
    main()
