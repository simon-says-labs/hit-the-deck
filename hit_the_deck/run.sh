#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
# Starts the configurator (ingress, port 8099) and the deck runtime.
set -o pipefail
export HTD_CONFIG_DIR=/config HTD_DATA_DIR=/data HTD_WEB_PORT=8099
cd /app || exit 1

# Configurator in the background, restarted if it ever stops.
(
  while true; do
    python3 -u webapp.py
    bashio::log.warning "Configurator stopped, restarting in 3 s"
    sleep 3
  done
) &

bashio::log.info "Starting Hit the Deck"
exec python3 -u runtime.py
