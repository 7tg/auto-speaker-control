import asyncio
import json
import logging
import os
import signal
import subprocess
import time

from tapo import ApiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("speaker-control")


def load_env(path: str = ".env") -> None:
    """Load key=value pairs from a .env file into os.environ."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
    except FileNotFoundError:
        pass


load_env()

TAPO_EMAIL = os.environ["TAPO_EMAIL"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
TAPO_IP = os.environ.get("TAPO_IP", "192.168.31.90")
IDLE_TIMEOUT = float(os.environ.get("IDLE_TIMEOUT", "900"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "0.5"))
SINK_MATCH = os.environ.get("SINK_MATCH", "Studio_24c")


async def connect_plug():
    """Connect to the Tapo smart plug."""
    client = ApiClient(TAPO_EMAIL, TAPO_PASSWORD)
    device = await client.generic_device(TAPO_IP)
    return device


async def get_device_on(device) -> bool:
    """Check if the device is currently on."""
    info = await device.get_device_info()
    return info.device_on


def is_audio_playing() -> bool:
    """Check if any audio stream is actively linked to the target sink."""
    try:
        result = subprocess.run(
            ["pw-dump"], capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout)
    except Exception:
        return False

    # Find sink node ID
    sink_node_id = None
    for obj in data:
        props = obj.get("info", {}).get("props", {})
        if (
            SINK_MATCH in props.get("node.name", "")
            and props.get("media.class") == "Audio/Sink"
        ):
            sink_node_id = obj["id"]
            break

    if sink_node_id is None:
        return False

    # Check for active links to this sink
    for obj in data:
        if obj.get("type") == "PipeWire:Interface:Link":
            info = obj.get("info", {})
            props = info.get("props", {})
            if (
                props.get("link.input.node") == sink_node_id
                and info.get("state") == "active"
            ):
                return True

    return False


async def main():
    log.info(
        "Starting speaker control (ip=%s, idle=%ss, poll=%ss, sink=%s)",
        TAPO_IP,
        IDLE_TIMEOUT,
        POLL_INTERVAL,
        SINK_MATCH,
    )

    device = await connect_plug()
    info = await device.get_device_info()
    log.info("Connected to %s (%s)", info.nickname, info.model)

    # Start with speakers OFF
    if info.device_on:
        await device.off()
        log.info("Turned speakers off (initial state)")
    speakers_on = False
    last_audio_time = None

    # Graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_signal():
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, handle_signal)
    loop.add_signal_handler(signal.SIGINT, handle_signal)

    while not shutdown_event.is_set():
        try:
            audio_active = is_audio_playing()

            if audio_active:
                last_audio_time = time.monotonic()
                if not speakers_on:
                    log.info("Audio detected, turning speakers on")
                    await device.on()
                    speakers_on = True
            else:
                if speakers_on and last_audio_time is not None:
                    idle_seconds = time.monotonic() - last_audio_time
                    if idle_seconds >= IDLE_TIMEOUT:
                        log.info(
                            "No audio for %d seconds, turning speakers off",
                            int(idle_seconds),
                        )
                        await device.off()
                        speakers_on = False
        except Exception as e:
            log.error("Error in main loop: %s", e)

        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=POLL_INTERVAL)
        except asyncio.TimeoutError:
            pass

    # Shutdown: turn off speakers with retry
    log.info("Shutting down, turning speakers off")
    for attempt in range(3):
        try:
            await device.off()
            log.info("Speakers turned off successfully")
            break
        except Exception as e:
            log.error("Shutdown attempt %d failed: %s", attempt + 1, e)


if __name__ == "__main__":
    asyncio.run(main())
