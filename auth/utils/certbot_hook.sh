#!/bin/bash

# Target directory for certificates
TARGET_DIR="/home/mame/certs"

# Ensure the target directory exists
mkdir -p "${TARGET_DIR}"

# Copy the latest certificates
cp /etc/letsencrypt/live/mame.lesen.digital/fullchain.pem "${TARGET_DIR}/fullchain.pem"
cp /etc/letsencrypt/live/mame.lesen.digital/privkey.pem "${TARGET_DIR}/privkey.pem"

# Set permissions
chmod 600 "${TARGET_DIR}/privkey.pem"
chown mame:mame "${TARGET_DIR}"/*

