# tldr-newsletter-slack
Route the TLDR Newsletter(s) to Slack because I don't check my email often enough.
![alt text](image.png)

### Docker setup

The container runs both the API and the daily newsletter schedule.

1. Create a Slack bot and copy its bot token.
2. Create Slack channels matching `#tldr-newsletter-{newsletter}`, for example `#tldr-newsletter-data`.
3. Copy `.env.example` to `.env` and set `SLACK_API_TOKEN`.
4. Start the app:

```
docker compose up -d
```

By default, the container posts `data,tech,devops,product,ai` at `06:00` in `America/Los_Angeles`. Change these env vars to customize it:

| Variable | Default | Purpose |
| --- | --- | --- |
| `TZ` | `America/Los_Angeles` | Container timezone for `SCHEDULE_TIME` |
| `SCHEDULER_ENABLED` | `true` | Enables the built-in daily scheduler |
| `SCHEDULER_RUN_ON_START` | `false` | Posts once when the container starts |
| `SCHEDULE_TIME` | `06:00` | Daily run time in `HH:MM` |
| `NEWSLETTERS` | `data,tech,devops,product,ai` | Comma-separated newsletter list |
| `SLACK_CHANNEL_PREFIX` | `tldr-newsletter-` | Prefix for default Slack channels |
| `ENABLE_CACHE` | `false` | Enables the persistent SQLite article cache |
| `CACHE_DATABASE_PATH` | `/data/tldr_cache.db` | SQLite cache path inside the container |

### Unraid setup

Use `unraid/tldr-newsletter-slack.xml` as the Unraid template. Required values are `SLACK_API_TOKEN`, `TZ`, `SCHEDULE_TIME`, and `NEWSLETTERS`.

To enable a persistent local cache in Unraid, set `ENABLE_CACHE=true` and keep the template default `CACHE_DATABASE_PATH=/data/tldr_cache.db`. The template mounts `/mnt/user/appdata/tldr-newsletter-slack` to `/data`, so the SQLite file persists across container restarts, image updates, and server reboots.

### Helpers

Interact with the API directly:

```
curl -X GET http://localhost:5000/articles?newsletter=data
```
