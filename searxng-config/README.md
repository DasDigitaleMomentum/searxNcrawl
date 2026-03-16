# searxng-config

This directory is mounted into the `searxng` container at `/etc/searxng` by `docker-compose.yml`.

## How it works

1. Start the stack once: `docker compose up --build`
2. SearXNG creates/uses `/etc/searxng/settings.yml`
3. Edit `settings.yml` in this folder to customize engines, formats, plugins, and limits
4. Restart SearXNG: `docker compose restart searxng`

## Recommended baseline

- Ensure `search.formats` includes `json` for API consumers.
- Remove optional/problematic engines in your environment (for example: `ahmia`, `torch`) to avoid startup engine-load warnings.
