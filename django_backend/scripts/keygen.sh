#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
KEYS_DIR="$PROJECT_ROOT/config/keys"

PRIVATE_KEY_FILE="$KEYS_DIR/jwt_private_key.pem"
PUBLIC_KEY_FILE="$KEYS_DIR/jwt_public_key.pem"

echo "🔐 Checking RSA keys for JWT authentication..."

if ! command -v openssl &> /dev/null; then
	echo "❌ OpenSSL not found. Please install OpenSSL."
	exit 1
fi

mkdir -p "$KEYS_DIR"

if [ ! -f "$PRIVATE_KEY_FILE" ]; then
	echo "🔑 Generating RSA private key..."
	openssl genrsa -out "$PRIVATE_KEY_FILE" 2048
	chmod 600 "$PRIVATE_KEY_FILE"
	echo "✅ Private key generated: $PRIVATE_KEY_FILE"
else
	echo "✅ Private key already exists: $PRIVATE_KEY_FILE"
	chmod 600 "$PRIVATE_KEY_FILE"
fi

if [ ! -f "$PUBLIC_KEY_FILE" ]; then
	echo "🔑 Generating RSA public key..."
	openssl rsa -in "$PRIVATE_KEY_FILE" -pubout -out "$PUBLIC_KEY_FILE"
	chmod 644 "$PUBLIC_KEY_FILE"
	echo "✅ Public key generated: $PUBLIC_KEY_FILE"
else
	echo "✅ Public key already exists: $PUBLIC_KEY_FILE"
	chmod 644 "$PUBLIC_KEY_FILE"
fi

echo "🎉 RSA keys are ready for JWT authentication!"
