import os
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def generate_keypair():
    private_key = X25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def serialize_public_key(public_key):
    return public_key.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )



def deserialize_public_key(data):
    return X25519PublicKey.from_public_bytes(data)



def derive_shared_key(private_key, peer_public_key):
    shared_secret = private_key.exchange(peer_public_key)

    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"Turkey-Chat",
    ).derive(shared_secret)

    return derived_key



def encrypt_message(key, message):
    cipher = ChaCha20Poly1305(key)
    nonce = os.urandom(12)

    ciphertext = cipher.encrypt(nonce, message.encode(), None)

    return nonce + ciphertext



def decrypt_message(key, data):
    cipher = ChaCha20Poly1305(key)

    nonce = data[:12]
    ciphertext = data[12:]

    plaintext = cipher.decrypt(nonce, ciphertext, None)

    return plaintext.decode()