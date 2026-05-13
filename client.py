import socket
import threading
import struct
import json
import queue
import requests
import customtkinter as ctk

from utils import (
    generate_keypair,
    serialize_public_key,
    deserialize_public_key,
    derive_shared_key,
    encrypt_message,
    decrypt_message,
    fingerprint,
)

PORT = 5000
REGISTRY_URL = "http://51.6.19.235:6467/servers"


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


class ChatApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")

        self.win = ctk.CTk()
        self.win.geometry("650x550")
        self.win.title("Turkey Chat")

        self.server_list = ctk.CTkTextbox(self.win, height=120)
        self.server_list.pack(fill="x", padx=10, pady=5)
        self.server_list.configure(state="disabled")

        self.refresh_btn = ctk.CTkButton(self.win, text="Refresh Servers", command=self.load_servers)
        self.refresh_btn.pack(pady=5)

        self.host_entry = ctk.CTkEntry(self.win, placeholder_text="Server IP")
        self.host_entry.pack(pady=5)

        self.connect_btn = ctk.CTkButton(self.win, text="Connect", command=self.start_connection)
        self.connect_btn.pack()

        self.chat_box = ctk.CTkTextbox(self.win)
        self.chat_box.pack(expand=True, fill="both", padx=10, pady=10)
        self.chat_box.configure(state="disabled")

        self.msg_entry = ctk.CTkEntry(self.win, placeholder_text="Message")
        self.msg_entry.pack(fill="x", padx=10)

        self.send_btn = ctk.CTkButton(self.win, text="Send", command=self.send)
        self.send_btn.pack(pady=5)

        self.sock = None
        self.shared_key = None
        self.private_key, self.public_key = generate_keypair()
        self.queue = queue.Queue()

        self.win.after(100, self.process_queue)

        self.load_servers()
        self.win.mainloop()

    def load_servers(self):
        try:
            r = requests.get(REGISTRY_URL, timeout=5)
            data = r.json()

            self.server_list.configure(state="normal")
            self.server_list.delete("1.0", "end")

            for s in data:
                line = f"{s['ip']}:{s['port']}"
                self.server_list.insert("end", line + "\n")

            self.server_list.configure(state="disabled")

        except Exception as e:
            self.append_chat(f"Server list error: {e}")

    def start_connection(self):
        host = self.host_entry.get()
        if not host:
            return

        threading.Thread(target=self.connect_worker, args=(host,), daemon=True).start()

    def connect_worker(self, host):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, PORT))

            send_packet(self.sock, serialize_public_key(self.public_key))

            peer_key = recv_packet(self.sock)
            peer_pub = deserialize_public_key(peer_key)

            self.verify_peer(peer_pub)

            self.shared_key = derive_shared_key(self.private_key, peer_pub)

            self.queue.put("Secure channel established")

            threading.Thread(target=self.receive_loop, daemon=True).start()

        except Exception as e:
            self.queue.put(f"Connection failed: {e}")

    def verify_peer(self, peer_pub):
        fp = fingerprint(peer_pub)

        try:
            with open("known_keys.txt", "r") as f:
                known = f.read().strip()
        except:
            known = None

        if known is None:
            with open("known_keys.txt", "w") as f:
                f.write(fp)
            self.queue.put("First connection trusted")
        elif known != fp:
            self.queue.put("WARNING: Key changed (possible MITM)")
        else:
            self.queue.put("Peer verified")

    def send(self):
        if not self.shared_key:
            return

        msg = self.msg_entry.get()
        if not msg:
            return

        packet = json.dumps({"type": "msg", "text": msg})
        encrypted = encrypt_message(self.shared_key, packet)

        send_packet(self.sock, encrypted)

        self.append_chat(f"You: {msg}")
        self.msg_entry.delete(0, "end")

    def receive_loop(self):
        while True:
            try:
                data = recv_packet(self.sock)
                if not data:
                    break

                msg = decrypt_message(self.shared_key, data)
                obj = json.loads(msg)

                if obj["type"] == "msg":
                    self.queue.put(f"Friend: {obj['text']}")

            except Exception:
                break

    def append_chat(self, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", text + "\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def process_queue(self):
        while not self.queue.empty():
            self.append_chat(self.queue.get())
        self.win.after(100, self.process_queue)


ChatApp()
