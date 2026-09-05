# Home presence tracker

Shows who's currently home by asking the router which devices are
connected to our WiFi and matching devices to people.

Runs on a Raspberry Pi that stays on at home. Polls the router on a
timer. Nothing is installed on the phones being tracked.

I check it from a web page on my phone, from home or from outside.

Current state only. No history, no database.

## Working style
I'm a beginner and want to understand what I'm building.
- One small step at a time, even within each logical part - dont make a whole step at once. buld it naturally.
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

## Steps
1. Get a list of connected devices out of the router and print it.  <- here
2. Let it run an hour; check whether devices appear and disappear steadily.
3. Map addresses to people so it prints names.
4. Serve it as a web page; open it on my phone at home.
5. Run it on the Pi, starting automatically on boot.
6. Add the mesh VPN so the same page works from outside the house.

## Status
Step 1. I don't yet know how my router exposes its device list.