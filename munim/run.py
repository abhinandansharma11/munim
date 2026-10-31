"""Start Munim.

    python run.py            -> http://localhost:8000 (laptop) and https://<laptop-ip>:8443 (phones; needed for the mic)
    python run.py --reset    -> also restore the demo data first
"""
import asyncio
import datetime
import ipaddress
import socket
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
CERT, KEY = ROOT / "data" / "cert.pem", ROOT / "data" / "key.pem"


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def make_cert(ip):
    """Self-signed certificate so phones get HTTPS (browsers only allow the microphone on HTTPS)."""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        print("  (install 'cryptography' to enable HTTPS for phone microphones)")
        return False
    CERT.parent.mkdir(exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Munim demo")])
    alt = x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address(ip)),
                                       x509.IPAddress(ipaddress.ip_address("127.0.0.1"))])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=30)).add_extension(alt, critical=False)
            .sign(key, hashes.SHA256()))
    KEY.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                      serialization.NoEncryption()))
    CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (CERT.parent / "cert_ip.txt").write_text(ip)
    return True


async def main():
    ip = lan_ip()
    if "--reset" in sys.argv:
        from server.main import db
        db.reset()
    ip_file = CERT.parent / "cert_ip.txt"
    https = CERT.exists() and ip_file.exists() and ip_file.read_text() == ip or make_cert(ip)
    servers = [uvicorn.Server(uvicorn.Config("server.main:app", host="0.0.0.0", port=8000, log_level="warning"))]
    if https:
        servers.append(uvicorn.Server(uvicorn.Config("server.main:app", host="0.0.0.0", port=8443, log_level="warning",
                                                     ssl_certfile=str(CERT), ssl_keyfile=str(KEY))))
    print("\n  Munim is running\n")
    print("  Laptop (console):   http://localhost:8000/console")
    print(f"  Phones, same Wi-Fi: https://{ip}:8443   (tap 'Advanced' -> 'Proceed' once)" if https else
          f"  Phones, same Wi-Fi: http://{ip}:8000")
    print("  Stop: Ctrl+C\n")
    await asyncio.gather(*(s.serve() for s in servers))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
