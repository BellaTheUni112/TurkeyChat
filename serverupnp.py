import socket
import threading
import struct
import miniupnpc
import signal
import sys
import requests
import time

HOST = "0.0.0.0"
PORT = 5000

# https://turkey112.online/register/

REGISTRY_URL = "http://51.6.19.235:6467/register"

waiting = []
waiting_lock = threading.Lock()

upnp = None
public_ip = None


def register_server(ip, port):
    try:
        payload = {
            "ip": ip,
            "port": port,
            "name": socket.gethostname()
        }

        r = requests.post(
            REGISTRY_URL,
            json=payload,
            timeout=5
        )

        print("Registered server:", r.status_code)

    except Exception as e:
        print("Failed to register server:", e)


def heartbeat_loop():
    while True:
        try:
            if public_ip:
                register_server(public_ip, PORT)

        except Exception as e:
            print("Heartbeat failed:", e)

        time.sleep(60)


def setup_upnp(port):
    try:
        upnp = miniupnpc.UPnP()

        print("Discovering UPnP devices...")
        upnp.discoverdelay = 200

        devices = upnp.discover()

        if devices == 0:
            print("No UPnP devices found")
            return None, None

        upnp.selectigd()

        local_ip = upnp.lanaddr
        external_ip = upnp.externalipaddress()

        print("Local IP:", local_ip)
        print("Public IP:", external_ip)

        existing = upnp.getspecificportmapping(port, "TCP")

        if existing:
            print(f"Port {port} already mapped")
        else:
            success = upnp.addportmapping(
                port,
                "TCP",
                local_ip,
                port,
                "TurkeyChat Server",
                ""
            )

            if success:
                print(f"UPnP opened TCP port {port}")
            else:
                print("Failed to open UPnP port")

        return upnp, external_ip

    except Exception as e:
        print("UPnP setup failed:", e)
        return None, None


def cleanup():
    global upnp

    print("\nShutting down...")

    if upnp:
        try:
            upnp.deleteportmapping(PORT, "TCP")
            print("Removed UPnP port mapping")
        except Exception as e:
            print("Failed to remove port mapping:", e)


def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def send_packet(sock, data):
    sock.sendall(struct.pack("!I", len(data)) + data)


def recv_exact(sock, size):
    data = b""

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if not chunk:
            return None

        data += chunk

    return data


def recv_packet(sock):
    raw = recv_exact(sock, 4)

    if not raw:
        return None

    length = struct.unpack("!I", raw)[0]

    if length > 10_000_000:
        print("Packet too large")
        return None

    return recv_exact(sock, length)


def close_socket(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass

    try:
        sock.close()
    except:
        pass


def relay(a, b):
    print("Relay started")

    def forward(src, dst):
        try:
            while True:
                data = recv_packet(src)

                if not data:
                    break

                send_packet(dst, data)

        except Exception as e:
            print("Relay error:", e)

        finally:
            close_socket(src)
            close_socket(dst)
            print("Connection closed")

    threading.Thread(
        target=forward,
        args=(a, b),
        daemon=True
    ).start()

    threading.Thread(
        target=forward,
        args=(b, a),
        daemon=True
    ).start()


print("Starting TurkeyChat server...")

upnp, public_ip = setup_upnp(PORT)

if public_ip:
    register_server(public_ip, PORT)

threading.Thread(
    target=heartbeat_loop,
    daemon=True
).start()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind((HOST, PORT))
server.listen()

print(f"Server running on {HOST}:{PORT}")

while True:
    try:
        client, addr = server.accept()

        print(f"Connected: {addr[0]}:{addr[1]}")

        client.settimeout(300)

        with waiting_lock:
            waiting.append(client)

            print(f"Waiting clients: {len(waiting)}")

            if len(waiting) >= 2:
                a = waiting.pop(0)
                b = waiting.pop(0)

                print("Pairing clients")

                relay(a, b)

    except Exception as e:
        print("Server error:", e)