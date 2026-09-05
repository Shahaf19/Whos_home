"""Ask the router the one question that needs no password, and print the answer."""

import requests

ROUTER_IP = "192.168.31.1"

url = f"http://{ROUTER_IP}/cgi-bin/luci/api/xqsystem/init_info"
reply = requests.get(url, timeout=10)

print(reply.json())
