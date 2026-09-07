"""Turning a list of devices into a list of people.

Knows nothing about routers, and nothing about how the answer gets displayed.
Give it a list of {"mac", "name"} from anywhere and it works the same.
"""

import json
from pathlib import Path

# Who lives here and which devices are theirs. Sits next to this file, so it
# is found no matter which folder the program was started from.
PEOPLE_FILE = Path(__file__).with_name("people.json")


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


def match(devices, mac_to_person):
    """Split devices into the people they belong to, and the leftovers.

    Gives back (people_home, strangers). Someone with two devices connected
    appears once - the question is who is here, not how many gadgets.
    """
    people_home = []
    strangers = []

    for device in devices:
        person = mac_to_person.get(device["mac"])
        if person is None:
            strangers.append(device)
        elif person not in people_home:
            people_home.append(person)

    return people_home, strangers
