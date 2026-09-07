# Who's home

A small web page that shows which people in the house are currently home.

Everyone's phone joins the WiFi, the router knows which devices are connected, and a file
maps devices to people. Phone connected → person home. Nothing is installed on the phones
being tracked, and no history is stored - current state only.

Python, Flask, and one reverse-engineered router API.

---

## Getting the data

Routers have no standard way to answer "who's connected?" Every manufacturer invented
their own, and mine - a Xiaomi running MiWiFi firmware - has no public documentation.

So I worked it out from the router's own admin page, using the browser's network inspector
to watch which requests it makes and copy them. Two useful things fell out of that:

- The login page loads a SHA-1 implementation, which gives away the scheme before you read
  any code: the password is hashed in the browser and never sent. Reproducing that hash
  correctly is the whole of the login.
- Every authenticated request follows one predictable shape, with a session token in the
  URL - so once you have one request, you have all of them.

The result is a login that exchanges a hashed password for a short-lived token, and
re-authenticates on its own when that token expires.

---

## Design

Four files, each responsible for one thing:

| File | Responsibility |
|---|---|
| `xiaomi.py` | Everything router-specific - address, login, device list |
| `presence.py` | Matching devices to people |
| `web.py` | The web page |
| `list_devices.py` | A terminal version, useful for watching changes live |

The split follows one rule: **only `xiaomi.py` knows what brand of router is in the
house.** It returns a plain list of `{"mac", "name"}`, so everything above it is unchanged
if the hardware changes. Adding a second router is a second file and one line:

```python
found = xiaomi.devices() + deco.devices()
```

`presence.py` knows nothing about routers *or* about display, which means it can be
exercised with a hand-written list of devices and no hardware at all.

---

## Decisions worth naming

**"Can't tell" is not "nobody home."** The most dangerous failure here isn't a crash, it's
a plausible wrong answer. If the router doesn't respond, the page says so explicitly rather
than rendering an empty list that reads as an empty house. The terminal version applies the
same rule: a failed poll leaves the previous state untouched instead of reporting that
everyone left at once.

**Credentials never enter the repository.** The router password is read from the
environment. The device-to-person mapping is gitignored, with a committed example showing
the format.

**Nothing is exposed to the internet.** The server only ever listens on the home network.
Remote access is handled outside the program by a mesh VPN, so the code is identical either
way and no port is ever opened.

**People, not devices.** Someone with a phone and a laptop connected is home once, not
twice. The unit of the answer is a person.

**The house has two networks.** A mesh unit upstairs runs its own subnet behind the main
router, so devices behind it are invisible to it - and the connection only works in one
direction. Rather than paper over that, the page states which part of the house it can
currently see.

---

## Running it

```powershell
$env:ROUTER_PASSWORD = Read-Host "Router password"
python web.py
```

Then open `http://<host>:5000` from any device on the network.

`people.example.json` shows the format for `people.json`.
