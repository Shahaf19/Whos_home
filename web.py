"""Serve the who's-home page on the local network."""

import time

import requests
from flask import Flask

import presence
import xiaomi

# Reuse an answer this many seconds old rather than asking the router again.
# Keeps a phone left on the page, or several people looking at once, from
# turning into a request each time.
CACHE_SECONDS = 15

# Read at startup, so a broken people file fails now rather than on the first
# visit from someone's phone.
people = presence.load_people(presence.PEOPLE_FILE)
mac_to_person = presence.index_by_mac(people)

# The last answer, and when we got it. Not history - one answer, replaced.
_cached = None
_cached_at = 0.0

# The page around the content. A plain string, not an f-string: CSS is full of
# { } and an f-string would need every one of them doubled.
SHELL = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>Who's home</title>
<style>
  body { font-family: system-ui, -apple-system, sans-serif;
         margin: 0; padding: 2rem 1.25rem;
         background: #faf9f7; color: #1c1c1c; }
  h1 { font-size: 1.4rem; margin: 0 0 1.5rem; font-weight: 600; }
  ul { list-style: none; margin: 0; padding: 0; }
  li { display: flex; justify-content: space-between; align-items: baseline;
       padding: 0.9rem 0; border-bottom: 1px solid #e5e2dd; font-size: 1.4rem; }
  li span { font-size: 0.95rem; }
  .home span { color: #1f7a3d; }
  .away { color: #9a9a9a; }
  .note { margin-top: 2rem; font-size: 0.85rem; color: #8a8a8a; line-height: 1.6; }
  @media (prefers-color-scheme: dark) {
    body { background: #16161a; color: #ececec; }
    li { border-bottom-color: #2c2c32; }
    .home span { color: #63c98a; }
    .away { color: #77777e; }
    .note { color: #77777e; }
  }
</style>
</head>
<body>
{content}
</body>
</html>
"""

app = Flask(__name__)


def render(content):
    """Wrap the page content in the shell."""
    return SHELL.replace("{content}", content)


def current_state():
    """Who is home, asking the router at most once every CACHE_SECONDS.

    Gives back (people_home, strangers). A failure is passed up rather than
    answered with a stale reading dressed up as a fresh one.
    """
    global _cached, _cached_at

    if _cached is not None and time.time() - _cached_at < CACHE_SECONDS:
        return _cached

    found = xiaomi.devices()
    _cached = presence.match(found, mac_to_person)
    _cached_at = time.time()
    return _cached


@app.route("/")
def page():
    try:
        home, strangers = current_state()
    except requests.exceptions.RequestException:
        # The router is not answering. Say that plainly. An empty list here
        # would read as "nobody is home", which is the one wrong answer this
        # page must never give.
        return render(
            "<h1>Can't tell</h1>"
            "<p class='note'>The router isn't answering, so there is no way "
            "to know who is home. This is not the same as nobody being in.</p>"
        )

    rows = ""
    for person in people:
        if person in home:
            rows += f"<li class='home'>{person}<span>home</span></li>"
        else:
            rows += f"<li class='away'>{person}<span>away</span></li>"

    return render(
        f"<h1>Who's home</h1>"
        f"<ul>{rows}</ul>"
        f"<p class='note'>{len(strangers)} unrecognised devices on the network."
        f"<br>Downstairs only - anything connected upstairs through the Deco "
        f"is not counted yet.</p>"
    )


# 0.0.0.0 means "accept connections on any address this machine has", so a
# phone on the same network can reach it. The default would only allow this
# machine to connect to itself.
app.run(host="0.0.0.0", port=5000)
