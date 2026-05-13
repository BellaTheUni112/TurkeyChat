TurkeyChat, an end-to-end encrypted chat app using ChaCha20Poly1305.

This currently only supports 2 people at a time.

V2 has MITM protection

To run a server, run server.py or server.exe but make sure you have port 5000 free and accessable.

The official server is hosted at turkey112.online


When you click connect, the server will wait for another client. while it is waiting, your client may become seemingly unresponsive, usually it has not crashed, it is just waiting for a second client.


# Known vulnerabilities

Unauthenticated Diffie-Hellman allows someone to perform an MITM attack

Weak TOFU

No racheting

No rekeying

No DoS protection/Rate limiting

Potential resource leaks

Metadata leakage
