"""Everything specific to the Xiaomi router.

The rest of the program calls devices() and never learns what brand of router
is in the house. Names starting with an underscore are internal to this file.
"""

import hashlib
import os
import random
import time

import requests

IP = "192.168.31.1"

# Read as this file is loaded, so a missing password stops the program at
# startup rather than on someone's first page load.
PASSWORD = os.environ.get("ROUTER_PASSWORD")
if not PASSWORD:
    raise SystemExit(
        'ROUTER_PASSWORD is not set. In PowerShell:\n'
        '    $env:ROUTER_PASSWORD = "your router admin password"'
    )

# The router's own MAC address, as reported by its newstatus reply. It goes
# into the nonce below. Not a secret.
MAC = "A4:39:B3:67:6D:21"

# Fixed string built into MiWiFi firmware, the same on every Xiaomi router.
# Not a secret either - it ships inside a JavaScript file anyone can download.
SALT = "a2ffa5c9be07488bbb04a3a47d3c5f6a"

TIMEOUT = 10

# The current session token. Kept in here so callers never have to know one
# exists. None means we have not logged in yet, or the last one was rejected.
_token = None


def _sha1(text):
    """Scramble text into a fixed-length value that cannot be reversed."""
    return hashlib.sha1(text.encode()).hexdigest()


def _log_in(password):
    """Exchange the password for a short-lived token."""
    # A one-time string, so the proof below is never the same twice. Without it,
    # anyone who recorded one login could replay it forever.
    nonce = f"0_{MAC}_{int(time.time())}_{random.randint(1000, 10000)}"

    # Salt on the inside, nonce on the outside. The router runs the same sum
    # against the password it has stored; matching results prove we knew it.
    # The password itself never leaves this machine.
    proof = _sha1(nonce + _sha1(password + SALT))

    reply = requests.post(
        f"http://{IP}/cgi-bin/luci/api/xqsystem/login",
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

    return reply["token"]


def _ask_for_devices(token):
    """The router's raw reply to the device-list question."""
    return requests.get(
        f"http://{IP}/cgi-bin/luci/;stok={token}/api/misystem/devicelist",
        timeout=TIMEOUT,
    ).json()


def devices():
    """Devices connected right now, as a list of {"mac", "name"}.

    Logs in when needed, including again if the token has expired. Lets a
    connection failure through to the caller, who decides what it means.
    """
    global _token

    if _token is None:
        _token = _log_in(PASSWORD)

    reply = _ask_for_devices(_token)

    if reply.get("code") != 0:
        # Most likely the token expired. Get a fresh one and ask again.
        _token = _log_in(PASSWORD)
        reply = _ask_for_devices(_token)

    if reply.get("code") != 0:
        raise SystemExit(f"The router would not give the device list: {reply}")

    # Translate into a shape that says nothing about Xiaomi. Upper case the
    # MAC here so nothing downstream has to think about it.
    found = []
    for device in reply["list"]:
        found.append({"mac": device["mac"].upper(), "name": device["name"]})
    return found
