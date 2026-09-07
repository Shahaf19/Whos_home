# Home presence tracker

Shows who's currently home by asking the router which devices are
connected to our WiFi and matching devices to people.

Runs on a Raspberry Pi that stays on at home. Asks the router when someone
opens the page, reusing the last answer if it is only seconds old - no
background timer. Nothing is installed on the phones being tracked.

I check it from a web page on my phone, from home or from outside.

Current state only. No history, no database.

## Working style
I'm a beginner and want to understand what I'm building.
- One small step at a time, even within each logical part - dont make a whole step at once. buld it naturally, yet be precised, deliberate and don't get too far out.
- Explain what a piece does and why, before writing it.
- Ask rather than guess when something about my setup matters.
- Don't add features I didn't ask for.

## Decisions made
- No phone app. A web page I open in the phone browser.
- The program only ever serves on the home network. Remote access is
  handled outside the program by a mesh VPN, so the code is the same
  either way. Never open a port on the router to the internet.
- The router password lives outside the code, never committed.
- One file holds everything router-specific; the rest of the program
  doesn't know what router I own.
- Router unreachable should show as "can't tell," not "nobody home."
- Develop on my laptop, deploy to the Pi. Nothing in the code changes.
- Two floors, two networks: Xiaomi downstairs, Deco upstairs running its own.
  Keeping them separate on purpose. The program queries both boxes and merges
  the results. One file per router, each answering "which devices can I see";
  nothing above them knows there are two.
- No configuration changes to either router. No port forwards, no bridge mode.
- The Pi lives upstairs on the Deco's network. That is the only spot that can
  reach both boxes: from inside the Deco's network the Xiaomi is reachable,
  but not the reverse - from the Xiaomi side the Deco refuses on both its
  addresses (checked 2026-09-06). Phones downstairs join the Deco's WiFi when
  they want the page.

## Steps
1. Get a list of connected devices out of the router and print it.  done
2. Let it run an hour; check whether devices appear and disappear steadily.  skipped
3. Map addresses to people so it prints names.  done
4. Serve it as a web page; open it on my phone at home.  done
5. Add the mesh VPN so the same page works from outside the house.  <- here

Optional, whenever they matter:
- Add the Deco as a second source and merge the two device lists. Until then
  the page says out loud that it only sees the downstairs network.
- Run it on the Pi, starting automatically on boot. Until then it runs on the
  laptop, so it only works while the laptop is on and at home.

## When the Pi arrives

To order, unless a kit already includes them:
- A Pi 4, 5, or Zero 2 W. Not a Pico - that is a microcontroller with no
  operating system and cannot run this.
- microSD card, 32 GB, A1 or A2 rated, known brand. It is the Pi's hard disk.
- Power supply. Pi 4 needs 5V/3A USB-C, Pi 5 wants 5V/5A. An ordinary phone
  charger causes random reboots that look like software faults.
- An SD card reader, if the laptop has no slot.

Setup, in order:
1. Flash the card with Raspberry Pi Imager. In its settings: set a hostname,
   enable SSH, and give it the Deco's WiFi - the only network that reaches
   both routers.
2. Boot it, then `ssh pi@<hostname>` from the laptop.
3. Install Tailscale on it first, so it is reachable by name from anywhere
   and its local address stops mattering.
4. `pip install flask requests`
5. `git clone` the repo.
6. Create people.json by hand. It is gitignored, so cloning does not bring it.
7. Run web.py by hand, open it from a phone, confirm it works.
8. Only then make it start on boot.

ROUTER_PASSWORD goes in the service definition, not a shell - otherwise it
disappears on every reboot.

## Status
Step 4. Steps 1 and 3 done: the Xiaomi answers api/misystem/devicelist after a
hashed-password login, and list_devices.py prints who is home by name.

Step 2 (the hour-long observation) was skipped, so how much devices flicker is
unmeasured.

Step 5 is stalled at the front door: the Deco web UI at 192.168.68.1 rejects
the password. Unresolved whether it wants a local password or the TP-Link
account one, and whether it authenticates locally or against TP-Link's
servers. Only reachable from the Deco's own network.

Until step 5 lands, the page must say it can only see the downstairs network.