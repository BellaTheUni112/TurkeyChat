import socket
import threading
import struct

HOST = "0.0.0.0"
PORT = 5000

waiting = None  # only supports 2 clients


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
    raw_len = recv_exact(sock, 4)
    if not raw_len:
        return None
    length = struct.unpack("!I", raw_len)[0]
    return recv_exact(sock, length)


def handle_pair(a, b):
    def relay(src, dst):
        while True:
            data = recv_packet(src)
            if not data:
                break
            send_packet(dst, data)

    threading.Thread(target=relay, args=(a, b)).start()
    threading.Thread(target=relay, args=(b, a)).start()


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print("Server running...")

while True:
    client, addr = server.accept()
    print("Connected:", addr)

    if waiting is None:
        waiting = client
        print("Waiting for second client...")
    else:
        print("Pairing clients")
        handle_pair(waiting, client)
        waiting = None