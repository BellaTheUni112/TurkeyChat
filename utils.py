import os
import hashlib

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


AAD = b"turkeychat-v2"


def generate_keypair():
    private_key = X25519PrivateKey.generate()
    return private_key, private_key.public_key()


def serialize_public_key(public_key):
    return public_key.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )


def deserialize_public_key(data):
    return X25519PublicKey.from_public_bytes(data)


def fingerprint(public_key):
    raw = serialize_public_key(public_key)
    return hashlib.sha256(raw).hexdigest()


def derive_shared_key(private_key, peer_public_key):
    shared_secret = private_key.exchange(peer_public_key)

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"Turkey-Chat",
    ).derive(shared_secret)


def encrypt_message(key, message: str):
    cipher = ChaCha20Poly1305(key)
    nonce = os.urandom(12)

    ct = cipher.encrypt(nonce, message.encode(), AAD)
    return nonce + ct


def decrypt_message(key, data: bytes):
    cipher = ChaCha20Poly1305(key)

    nonce = data[:12]
    ct = data[12:]

    pt = cipher.decrypt(nonce, ct, AAD)
    return pt.decode()
