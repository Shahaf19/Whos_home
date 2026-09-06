# Who's home

A small program that tells me which people in the house are currently home.

Everyone's phone connects to our WiFi, the router knows which devices are connected, and
I keep a list matching each device to a person. Phone connected → person home. Runs on
one always-on machine, asks the router every 30 seconds or so, installs nothing on the
phones.

Built one step at a time. Each step gets added below.

---

## Step 1 — get a device list out of the router ✅

There's no standard way to ask a router "who's connected?" Every manufacturer invented
their own, and some don't let you ask at all. So this had to be settled before building
anything.

### Working out what I'm dealing with

| Question | How I asked | Answer |
|---|---|---|
| Which box is my PC using as its router? | `Get-NetIPConfiguration` | Me at `192.168.31.201`, gateway `192.168.31.1` |
| Is that box actually the way out to the internet? | `tracert -d -h 4 8.8.8.8` | Yes — hop 1 is the gateway itself |
| What make is it? | `curl.exe http://192.168.31.1/` | Page title 小米路由器 ("Xiaomi Router") |
| Which model, and will it talk without a password? | `api/xqsystem/init_info` | `xiaomi.router.ra72`, firmware `1.0.122`. Answers with no password |
| How do I ask it for real data? | Chrome, F12 → Network tab, then log in | See below |

The Network tab was the one that mattered. It shows every request the router's own admin
page makes — so instead of guessing, I watched the page do the work and copied it. Two
things fell out:

- **The login page loads `sha1.js`.** A login page only needs a hash function if it plans
  to scramble the password in the browser and send the result. So the router never
  receives the actual password — which told me the shape of the login before I wrote any
  code.
- **Every logged-in request has the same shape:**
  `http://192.168.31.1/cgi-bin/luci/;stok=<token>/api/<module>/<question>`

`api/misystem/devicelist` is the one that returns connected devices — `mac`, `name`, `ip`
and `online` for each.

### Two networks, not one

| | Address | What it is |
|---|---|---|
| **Xiaomi** | `192.168.31.1` | The real router. Everything reaches the internet through it. |
| **Deco S7** | `192.168.68.1` | Sold as an extender, but runs its own separate network behind the Xiaomi. |

The Deco shows up on the Xiaomi as one ordinary device at `192.168.31.89`. Anything
connected *through* it is invisible — the Xiaomi genuinely doesn't know those devices
exist, it just sees one box using a lot of bandwidth. My PC has moved between the two
networks on its own, without me touching anything.

### The script

`list_devices.py`. Five things in order:

1. **Reads the password** from the `ROUTER_PASSWORD` environment variable. Never in the
   file — git remembers everything, so a password committed once is in the history
   forever.
2. **Proves I know it, without sending it.** Builds `SHA1(nonce + SHA1(password + salt))`,
   where the nonce is a one-time string. Only the nonce and the result get sent; the
   router runs the same sum against what it has stored and compares. The password never
   leaves this machine. The nonce is there so the same number is never sent twice.
3. **Gets a token back**, so the password step happens once.
4. **Asks `devicelist`** with that token.
5. **Prints** name, IP and MAC per device.

The salt in the code is a fixed string built into MiWiFi firmware — identical on every
Xiaomi router and published in a JavaScript file anyone can download. It's in the file
because it genuinely isn't a secret.

### Tests

| Test | Result |
|---|---|
| No password set | Clear message, nothing else |
| Wrong password on purpose | Router refused. Proves the request was built right and was actually checked — a malformed request fails differently |
| WiFi off entirely | Fails instantly, clear message |
| Pointed at a dead address | Waits 10s for the timeout, then a clear message |
| Real password | Four devices, including this PC at the address I already knew |
| iPhone WiFi off, re-ran | Gone immediately. The test that decided the project — the router reports who's connected *now*, not everything it's ever seen |

Every failure prints **nothing** about devices. Not an empty list, not a zero — nothing at
all. "Can't tell" must never look like "nobody home."

### Still open

- **The Deco blind spot.** Deferred, not solved. Either query both boxes and merge the
  results, or put the Deco into bridge mode so there's only one network. Decide after
  step 2.
- **Token expiry.** The token dies eventually. Doesn't matter yet — the script logs in and
  exits — but a version that runs for days has to notice a rejected token and log in
  again, without reporting an empty house while it does.
- **Two devices use invented MAC addresses.** Apple devices make up a MAC per network for
  privacy. Stable here, so matching devices to people will work — but if someone toggles
  the private-address setting they get a new one and silently stop being recognised.
- **Unverified parts of the nonce.** It contains the router's MAC and a timestamp. I don't
  know whether the router reads either one; I'm copying the format because it works.
- **Only the polite departure is tested.** Turning WiFi off makes the phone announce it's
  leaving, so the router drops it instantly — that's why the test was immediate. Actually
  walking out of the house doesn't announce anything; the phone drifts out of range and
  the router waits for a timeout before deciding it's gone. That delay is the real lag on
  the tracker and it's still unmeasured. Step 2 should show it.

### Running it

```powershell
$env:ROUTER_PASSWORD = Read-Host "Router password"
python list_devices.py
```

Typing the password directly with `$env:ROUTER_PASSWORD = "..."` also works, but PowerShell
saves it to your command history file in plain text. `Read-Host` prompts instead.

