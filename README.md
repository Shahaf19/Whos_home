# Who's home

A small program that tells me which people in the house are currently home.

Everyone's phone connects to our WiFi, the router knows which devices are connected, and
I keep a list matching each device to a person. Phone connected → person home. Runs on
one always-on machine, asks the router every 30 seconds or so, installs nothing on the
phones.

Built one step at a time. Each step gets added below.

---

## Step 1 — can we get a device list out of the router at all? ✅ Works

There's no standard way to ask a router "who's connected?" — every manufacturer invented
their own, and some don't let you ask at all. So this got settled before building
anything else.

### Working out what we're dealing with


| Query | What it was asking | What came back |
|---|---|---|
| `Get-NetIPConfiguration` | Which box is this PC using as its router? | Gateway `192.168.68.1` |
| `arp -a` | Who else is on this network? | The handful of devices this PC had recently talked to |
| `curl http://192.168.68.1/` | What make is that box? Brand decides the whole approach. | A page loading `tpEncrypt.js` → TP-Link |
| `tracert -d -h 4 8.8.8.8` | Is that box actually the way out to the internet? | No. First stop was `192.168.31.1` — something else sits in between |
| `curl http://192.168.31.1/` | Then what is *this* one? | Page title 小米路由器 ("Xiaomi Router") → the real router |
| `.../api/xqsystem/init_info` | Exact model and firmware — decides whether a known way in exists | `xiaomi.router.ra72`, firmware `1.0.122`, Chinese region. No password needed |
| `.../api/xqsystem/router_info` | Will it hand over private data, and is there a way to ask? | `{"code":401,"msg":"Invalid token"}` → "I'll tell you, but log in first" |

### What we found

Two separate networks, not one:

| | Address | What it is |
|---|---|---|
| **Xiaomi** | `192.168.31.1` | The actual router. Everything reaches the internet through it. |
| **Deco S7** | `192.168.68.1` | Sold as an extender, but runs its own separate network behind the Xiaomi. It shows up on the Xiaomi as a single ordinary device at `192.168.31.89`. |

### The script

`list_devices.py` logs into the Xiaomi and prints what's connected. Four steps:

1. **Reads the password** from the `ROUTER_PASSWORD` environment variable, so it never
   sits in the file.
2. **Proves we know it, without sending it.** The router won't take a plain password.
   So the script invents a one-time random string (a *nonce*), scrambles it together with
   the password through SHA-1 — easy to compute, effectively impossible to reverse — and
   sends only the scrambled result. The router runs the same sum against the password it
   has stored; matching results prove we knew it. The nonce is what stops anyone who
   recorded the exchange from replaying it later.
3. **Gets a token** (`stok`) back — a temporary pass, so the password step happens once.
4. **Asks for the device list** with that token, and prints name / IP / MAC.

Both requests have timeouts. Anything that fails — no password set, router unreachable,
login refused — prints what went wrong and exits non-zero rather than pretending it
returned an empty house.

### Tests run

1. **No password set** → clear error message. Checked the failure path before trusting
   the success path.
2. **Wrong password on purpose** → router replied `not auth`. This mattered: it proved
   the request was built correctly and the router had actually checked it. A malformed
   request fails differently. Only unknown left was the password itself.
3. **Real password** → 4 devices, including this PC at the address we already knew.
4. **iPhone WiFi off, waited, re-ran** → iPhone gone, 4 down to 3. The one that decided
   the project: proves the router reports who's connected *right now*, not everything
   it's ever seen.

### Open problems

- **Deco blind spot.** The Xiaomi can't see anything connected through the Deco, so
  the whole house currently shows as 3 devices. Needs deciding: query both boxes and
  combine, or reconfigure the Deco so there's only one network.

### Running it

```bash
export ROUTER_PASSWORD="..."      # bash
$env:ROUTER_PASSWORD = "..."      # PowerShell
python list_devices.py
```


