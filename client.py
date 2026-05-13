import socket
import threading
import struct
import customtkinter as ctk

from utils import (
    generate_keypair,
    serialize_public_key,
    deserialize_public_key,
    derive_shared_key,
    encrypt_message,
    decrypt_message,
)


PORT = 5000

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
        self.win.geometry("600x500")
        self.win.title("Turkey Chat")

        self.host_entry = ctk.CTkEntry(
            self.win,
            placeholder_text="Connect to Turkey Chat server: "
        )
        self.host_entry.pack(pady=10)

        self.connect_btn = ctk.CTkButton(
            self.win,
            text="Connect",
            command=self.start_connection
        )
        self.connect_btn.pack(pady=5)

        self.chat_box = ctk.CTkTextbox(self.win)
        self.chat_box.pack(expand=True, fill="both", padx=10, pady=10)
        self.chat_box.configure(state="disabled")

        self.msg_entry = ctk.CTkEntry(self.win, placeholder_text="Type message...")
        self.msg_entry.pack(fill="x", padx=10, pady=5)

        self.send_btn = ctk.CTkButton(self.win, text="Send", command=self.send)
        self.send_btn.pack(pady=5)

        self.sock = None
        self.shared_key = None

        self.private_key, self.public_key = generate_keypair()

        self.win.mainloop()

    def start_connection(self):
        HOST = self.host_entry.get()

        if not HOST:
            self.append_chat("Enter a server IP first.")
            return

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        send_packet(self.sock, serialize_public_key(self.public_key))

        peer_key = recv_packet(self.sock)
        peer_public = deserialize_public_key(peer_key)

        self.shared_key = derive_shared_key(self.private_key, peer_public)

        self.append_chat("System: Secure channel established")

        threading.Thread(target=self.receive_loop, daemon=True).start()

    def append_chat(self, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", text + "\n")
        self.chat_box.see("end")
        self.chat_box.configure(state="disabled")

    def send(self):
        if not self.shared_key:
            return

        msg = self.msg_entry.get()
        if not msg:
            return

        encrypted = encrypt_message(self.shared_key, msg)
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
                self.append_chat(f"Friend: {msg}")

            except Exception as e:
                self.append_chat(f"Error: {e}")
                break


ChatApp()