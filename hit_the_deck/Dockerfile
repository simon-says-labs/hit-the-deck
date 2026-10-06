FROM ghcr.io/home-assistant/base:3.24-2026.08.0

# Everything from Alpine (no compiler needed):
#  python3 with Pillow, PyYAML, aiohttp, websockets
#  hidapi + libusb: native libraries the Stream Deck library loads
#  eudev-libs: device discovery; font-dejavu: the text font on the keys
RUN apk add --no-cache \
      python3 py3-pip py3-pillow py3-yaml py3-aiohttp py3-websockets \
      hidapi libusb eudev-libs font-dejavu

# python-elgato-streamdeck is pure Python; --no-deps keeps Pillow from Alpine.
RUN pip3 install --no-cache-dir --break-system-packages --no-deps "streamdeck==0.10.0"

COPY app/ /app/

# s6-overlay starts the service; finish stops the whole container when the deck is gone,
# so the Supervisor's watchdog starts a fresh one that sees the new USB device.
COPY run.sh /etc/services.d/hit-the-deck/run
COPY finish /etc/services.d/hit-the-deck/finish
RUN chmod a+x /etc/services.d/hit-the-deck/run /etc/services.d/hit-the-deck/finish

WORKDIR /app

LABEL \
  io.hass.type="app" \
  io.hass.arch="aarch64|amd64" \
  org.opencontainers.image.source="https://github.com/simon-says-labs/hit-the-deck" \
  org.opencontainers.image.licenses="MIT"
