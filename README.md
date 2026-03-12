# Auto Speaker Control

Automatic power management for speakers connected to a TP-Link Tapo smart plug. Monitors PipeWire audio streams and turns speakers on when audio plays, off after idle timeout, and off at system shutdown.

Built for speakers that lack a standby feature (e.g., PreSonus Eris E5).

## How It Works

- Polls PipeWire (`pw-dump`) every 0.5s for active audio streams linked to a specific sink
- Turns the Tapo smart plug **on** when audio starts playing
- Turns it **off** after a configurable idle timeout (default: 15 minutes)
- Turns it **off** gracefully on service stop or system shutdown (SIGTERM)
- Speakers stay **off** at startup until audio is detected

## Requirements

- Linux with PipeWire
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- TP-Link Tapo smart plug (P100/P105/P110/etc.)
- Third-Party Compatibility enabled in the Tapo app (Me > Third-Party Services)

## Setup

1. Clone the repo and create your `.env`:

```sh
cp .env.example .env
```

2. Edit `.env` with your TP-Link account credentials and settings:

```
TAPO_EMAIL=your-email@example.com
TAPO_PASSWORD=your-password
TAPO_IP=192.168.31.90
IDLE_TIMEOUT=900
POLL_INTERVAL=0.5
SINK_MATCH=Studio_24c
```

| Variable | Description | Default |
|---|---|---|
| `TAPO_EMAIL` | TP-Link account email | (required) |
| `TAPO_PASSWORD` | TP-Link account password | (required) |
| `TAPO_IP` | Smart plug IP address | `192.168.31.90` |
| `IDLE_TIMEOUT` | Seconds of silence before turning off | `900` (15 min) |
| `POLL_INTERVAL` | Seconds between audio checks | `0.5` |
| `SINK_MATCH` | PipeWire sink name substring to match | `Studio_24c` |

3. Install and start the systemd service:

```sh
./install.sh
```

## Usage

```sh
# Check status
systemctl --user status speaker-control

# Watch logs
journalctl --user -u speaker-control -f

# Stop (turns off speakers)
systemctl --user stop speaker-control

# Restart
systemctl --user restart speaker-control

# Disable autostart
systemctl --user disable speaker-control
```

## Manual Run

```sh
uv run python speaker_control.py
```

## Resource Usage

- ~19 MB memory
- ~1.5% CPU (at 0.5s poll interval)

## License

MIT
