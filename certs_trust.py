"""Certificate trust for sites that fail to send their intermediate certificate: certifi plus the public intermediates in certs/.
Verification stays on; this only completes chains the server should have sent itself."""
import tempfile
from pathlib import Path

import certifi

_bundle = None


def trust():
    global _bundle
    if _bundle is None:
        extra = sorted(Path(__file__).parent.glob("certs/*.pem"))
        if not extra:
            _bundle = True
        else:
            with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as f:
                for p in [Path(certifi.where())] + extra:
                    f.write(p.read_bytes() + b"\n")
            _bundle = f.name
    return _bundle
