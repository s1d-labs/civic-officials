"""Certificate trust for sites that fail to send their intermediate certificate: certifi plus the public intermediates that
scrape-hub-client ships (scrape_hub_client/certs/ in s1d-labs/runner, ca_bundle()). Verification stays on; this only completes
chains the server should have sent itself. A new intermediate goes into s1d-labs/runner, not into this repo."""
from scrape_hub_client import ca_bundle


def trust():
    return ca_bundle()
