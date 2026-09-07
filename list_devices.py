"""Say who is home, by matching connected devices against people.json.

Prints only when someone arrives or leaves. Ctrl+C to stop.
"""

import time

import requests

import presence
import xiaomi

# How long to wait between rounds. Turn it down while testing.
POLL_SECONDS = 3

# Load this before touching the network, so a typo in the file fails at once
# rather than after a round trip to the router.
people = presence.load_people(presence.PEOPLE_FILE)
mac_to_person = presence.index_by_mac(people)
print("People:", ", ".join(people))

# What the last round saw: people who were home, plus unrecognised devices.
# None means no round has happened yet. Only ever holds one round; nothing
# accumulates.
previous = None

while True:
    now = time.strftime("%H:%M:%S")

    try:
        found = xiaomi.devices()
    except requests.exceptions.RequestException as problem:
        # We cannot tell who is home. Leave 'previous' untouched - treating a
        # failed round as an empty house would print a departure for everyone.
        print(now, "can't tell -", problem)
        time.sleep(POLL_SECONDS)
        continue

    home, strangers = presence.match(found, mac_to_person)

    # Keyed so the comparison below works: people by name, strangers by MAC.
    current = {}
    for person in home:
        current[person] = person
    for device in strangers:
        current[device["mac"]] = f"? {device['name']} {device['mac']}"

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
