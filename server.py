import socket
import threading
import struct

HOST = "0.0.0.0"
PORT = 5000

waiting = []


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
    return recv_exact(sock, length)


def relay(a, b):
    def forward(src, dst):
        while True:
            data = recv_packet(src)
            if not data:
                break
            send_packet(dst, data)

    threading.Thread(target=forward, args=(a, b), daemon=True).start()
    threading.Thread(target=forward, args=(b, a), daemon=True).start()


print("Server running at", HOST, PORT)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()


while True:
    client, addr = server.accept()
    print("Connected:", addr)

    waiting.append(client)

    if len(waiting) >= 2:
        a = waiting.pop(0)
        b = waiting.pop(0)

        print("Pairing clients")
        relay(a, b)
