#!/usr/bin/env bash
# setup_connection.sh
# Reads CLOUDANT_URL and CLOUDANT_APIKEY from .env and creates the
# cloudant_creds connection in Orchestrate for draft and live environments.
# Never prints the values.

set -euo pipefail

ENV_FILE="$(dirname "$0")/../.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: .env file not found at $ENV_FILE"
  exit 1
fi

# Read values from .env without printing them.
# Lines must be in the form KEY=value (no export prefix required).
CLOUDANT_URL=$(grep -E '^CLOUDANT_URL=' "$ENV_FILE" | head -1 | cut -d'=' -f2-)
CLOUDANT_APIKEY=$(grep -E '^CLOUDANT_APIKEY=' "$ENV_FILE" | head -1 | cut -d'=' -f2-)

if [ -z "$CLOUDANT_URL" ]; then
  echo "ERROR: CLOUDANT_URL not found in .env"
  exit 1
fi

if [ -z "$CLOUDANT_APIKEY" ]; then
  echo "ERROR: CLOUDANT_APIKEY not found in .env"
  exit 1
fi

echo "Adding connection cloudant_creds..."
orchestrate connections add -a cloudant_creds

echo "Configuring cloudant_creds for draft environment..."
orchestrate connections configure \
  -a cloudant_creds \
  --env draft \
  -t team \
  -k key_value

echo "Configuring cloudant_creds for live environment..."
orchestrate connections configure \
  -a cloudant_creds \
  --env live \
  -t team \
  -k key_value

echo "Setting credentials for draft environment..."
orchestrate connections set-credentials \
  -a cloudant_creds \
  --env draft \
  -e "url=$CLOUDANT_URL" \
  -e "apikey=$CLOUDANT_APIKEY"

echo "Setting credentials for live environment..."
orchestrate connections set-credentials \
  -a cloudant_creds \
  --env live \
  -e "url=$CLOUDANT_URL" \
  -e "apikey=$CLOUDANT_APIKEY"

echo "Done. Connection cloudant_creds is set for draft and live."
