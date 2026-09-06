"""Say who is home, by matching connected devices against people.json.

Prints only when someone arrives or leaves. Ctrl+C to stop.
"""

import hashlib
import json
import os
import random
import time
from pathlib import Path

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

# Who lives here and which devices are theirs. Sits next to this script, so it
# is found no matter which folder the program was started from.
PEOPLE_FILE = Path(__file__).with_name("people.json")


def sha1(text):
    """Scramble text into a fixed-length value that cannot be reversed."""
    return hashlib.sha1(text.encode()).hexdigest()


def load_people(path):
    """Read the people file. Gives back person -> list of device MACs."""
    if not path.exists():
        raise SystemExit(
            f"{path.name} not found. Copy people.example.json to {path.name} "
            "and fill in who lives here and which devices are theirs."
        )

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as problem:
        raise SystemExit(f"{path.name} is not valid JSON: {problem}")


def index_by_mac(people):
    """Flip person -> [devices] into device -> person.

    The file is written the way a human thinks about it. The router hands us
    a MAC and asks whose it is, so we need it the other way round.
    """
    by_mac = {}
    for person, macs in people.items():
        for mac in macs:
            # Upper case on both sides, so 9e:23 matches 9E:23.
            by_mac[mac.upper()] = person
    return by_mac


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

# Load this before touching the network, so a typo in the file fails at once
# rather than after a round trip to the router.
people = load_people(PEOPLE_FILE)
mac_to_person = index_by_mac(people)
print("People:", ", ".join(people))

try:
    token = log_in(password)
except requests.exceptions.RequestException as problem:
    # Can't reach the router at all on the way in. Stop, rather than pretend.
    raise SystemExit(f"Could not reach the router at {ROUTER_IP}: {problem}")

# What the last round saw: people who were home, plus unrecognised devices.
# None means no round has happened yet. Only ever holds one round; nothing
# accumulates.
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

    # Who is here, plus anything we don't recognise. Keyed by person for known
    # devices, so someone with two devices on only counts once.
    current = {}
    for device in devices_reply["list"]:
        mac = device["mac"].upper()
        person = mac_to_person.get(mac)
        if person:
            current[person] = person
        else:
            current[mac] = f"? {device['name']} {mac}"

    if previous is None:
        print(now, "home:", ", ".join(current.values()))
    else:
        for key in current:
            if key not in previous:
                print(now, "ARRIVED", current[key])
        for key in previous:
            if key not in current:
                print(now, "LEFT   ", previous[key])

    previous = current
    time.sleep(POLL_SECONDS)
