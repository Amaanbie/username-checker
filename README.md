# Username Checker

A fast, real-time username availability checker that probes 1,000+ platforms in parallel and streams results to the browser over Server-Sent Events.

## Features

- Checks 1,000+ social, gaming, dev, and creative platforms
- Live streaming results (SSE) — no waiting for the slowest site
- Filter by status (available / taken / unknown) and category
- Zero JS dependencies on the frontend
- Single-file Flask backend

## Local development

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://localhost:5000>.

### Environment variables

| Variable          | Default     | Purpose                                          |
|-------------------|-------------|--------------------------------------------------|
| `PORT`            | `5000`      | Local dev port                                   |
| `HOST`            | `127.0.0.1` | Bind address                                     |
| `LOG_LEVEL`       | `INFO`      | Python logging level                             |
| `REQUEST_TIMEOUT` | `8`         | Per-site HTTP timeout (seconds)                  |
| `MAX_WORKERS`     | `50`        | Thread-pool size for parallel checks             |
| `FLASK_DEBUG`     | `0`         | Set `1` to enable Flask debug mode (dev only)    |

Copy `.env.example` to `.env` to customize locally.

## Deploying to Vercel

1. Push this repo to GitHub.
2. In Vercel, **Add New → Project → Import** the GitHub repo.
3. Framework preset: **Other**. Build/output settings can stay at defaults — `vercel.json` handles routing to the Python runtime.
4. (Optional) Add the env vars above under **Project Settings → Environment Variables**.
5. Deploy.

The `vercel.json` sets `maxDuration: 60` for the function. On the Hobby tier this is the cap; if the streaming check takes longer than 60s for some usernames, raise `MAX_WORKERS` or lower `REQUEST_TIMEOUT`. On Pro/Enterprise you can raise `maxDuration` accordingly.

## Project layout

```
app.py              # Flask app — routes, SSE stream, per-site probe
sites.py            # Platform definitions (1,000+ entries)
templates/
  index.html        # Single-page UI
api/
  index.py          # Vercel entry point (re-exports the Flask app)
vercel.json         # Vercel routing + function config
requirements.txt    # Python dependencies
```

## How detection works

Each site entry in `sites.py` declares an `errorType` indicating how to interpret a response:

- `status_code` — `2xx` = taken, `404` = available, anything else inconclusive
- `message` — body contains `errorMsg` → username is available
- `response_url` — final redirected URL contains `errorUrl` → username is available

`403` and `429` responses are always treated as inconclusive (bot-block / rate-limit).

## Credits

Platform list seeded from the [Sherlock](https://github.com/sherlock-project/sherlock) project with custom additions.

## License

MIT — see [LICENSE](LICENSE).
