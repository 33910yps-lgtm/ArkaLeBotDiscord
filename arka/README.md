# ARKA Bot

A Discord bot for the VRChat "Arkana" community with music playback (Lavalink) and a lightweight web dashboard.

## Quick Start

1. Extract the archive.
2. Run `sudo bash install.sh` (or `bash install.sh` if you are root).
3. The bot will start, the dashboard will be available at `http://<your-pi-ip>:8080`.
4. Use the dashboard to set your VRChat auth cookie (or use `/vrchat setcookie` in Discord).
5. Enjoy music with `/music play <query>` and VRChat updates in the configured channel.

## Services

- `arka.service` – runs the bot + dashboard.
- `lavalink.service` – runs a local Lavalink node (if enabled).

## Logs

View logs with `journalctl -u arka.service -f` and `journalctl -u lavalink.service -f`.

## Update

Run `./update.sh` (placeholder – replace with your own update logic).