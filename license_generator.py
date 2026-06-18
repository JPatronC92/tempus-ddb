import argparse
import secrets
import string
import datetime
import json
import os
import hmac
import hashlib

# This MUST match the LICENSE_SECRET in src/lib.rs for keys to validate.
# In production, this would be fetched from a secure server.
LICENSE_SECRET = b"tempus-ddb-hmac-secret-key-v1-2026"


def generate_license_key(prefix="tmb_live_", random_length=24):
    """
    Generates a cryptographically secure license key with HMAC-SHA256 verification.

    Format: tmb_live_{random_part}_{hmac_hex_signature}

    The HMAC is computed over random_part using LICENSE_SECRET, ensuring that
    only keys generated with the correct secret will pass validation.
    """
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(random_length))

    # Compute HMAC-SHA256 of the random part
    hmac_sig = hmac.new(LICENSE_SECRET, random_part.encode('utf-8'), hashlib.sha256).hexdigest()

    return f"{prefix}{random_part}_{hmac_sig}"


def create_license(client_name, tier, valid_days=365, output_file="licenses.json"):
    """Creates a license and stores it in a registry."""
    key = generate_license_key()

    issue_date = datetime.datetime.now()
    expiry_date = issue_date + datetime.timedelta(days=valid_days)

    license_data = {
        "client_name": client_name,
        "tier": tier,
        "license_key": key,
        "issue_date": issue_date.isoformat(),
        "expiry_date": expiry_date.isoformat(),
        "status": "active"
    }

    # Load existing registry or create new
    registry = []
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            try:
                registry = json.load(f)
            except json.JSONDecodeError:
                pass

    registry.append(license_data)

    with open(output_file, "w") as f:
        json.dump(registry, f, indent=4)

    return license_data


def main():
    parser = argparse.ArgumentParser(description="Tempus DDB - Generador de Licencias B2B (HMAC-SHA256)")
    parser.add_argument("client_name", help="Nombre del cliente B2B")
    parser.add_argument("--tier", choices=["startup", "enterprise", "unlimited"], default="startup",
                        help="Nivel del servicio contratado")
    parser.add_argument("--days", type=int, default=365, help="Días de validez de la licencia (default: 365)")

    args = parser.parse_args()

    print(f"Generando nueva licencia para el cliente: {args.client_name} (Tier: {args.tier})")

    lic = create_license(args.client_name, args.tier, args.days)

    print("\n--- LICENCIA GENERADA CON ÉXITO ---")
    print(f"CLIENTE: {lic['client_name']}")
    print(f"TIER: {lic['tier'].upper()}")
    print(f"EXPIRACIÓN: {lic['expiry_date']}")
    print(f"🔑 LICENSE KEY: {lic['license_key']}")
    print("-----------------------------------")
    print("Guarda esta clave y entrégala al cliente. Ya está registrada en 'licenses.json'.")


if __name__ == "__main__":
    main()
