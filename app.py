import json
import logging
import os
import re
import concurrent.futures
from flask import Flask, render_template, Response, request, jsonify
import requests
from sites import SITES, CATEGORIES

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("username-checker")

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "8"))
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "50"))
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


def check_site(name: str, site: dict, username: str) -> dict:
    url = site["url"].format(username)
    error_type = site.get("errorType", "status_code")

    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        # Treat 403 (bot-blocked) and 429 (rate-limited) as inconclusive
        if r.status_code in (403, 429):
            status = "error"
        elif error_type == "status_code":
            if 200 <= r.status_code < 300:
                status = "taken"
            elif r.status_code == 404:
                status = "available"
            else:
                # 3xx, 5xx, 999 (LinkedIn), etc. — inconclusive
                status = "error"
        elif error_type == "message":
            error_msg = site.get("errorMsg", "")
            status = "available" if error_msg in r.text else "taken"
        elif error_type == "response_url":
            error_url = site.get("errorUrl", "")
            status = "available" if error_url in r.url else "taken"
        else:
            status = "taken" if 200 <= r.status_code < 300 else "error"

    except requests.exceptions.Timeout:
        status = "timeout"
    except requests.exceptions.RequestException:
        status = "error"
    except Exception:
        log.exception("unexpected error checking %s", name)
        status = "error"

    return {
        "name": name,
        "url": url,
        "urlMain": site.get("urlMain", ""),
        "category": site.get("category", "Other"),
        "status": status,
    }


@app.route("/")
def index():
    return render_template("index.html", total=len(SITES), categories=CATEGORIES)


@app.route("/healthz")
def healthz():
    return jsonify(status="ok", platforms=len(SITES))


@app.route("/sites-list")
def sites_list():
    data = [
        {"name": name, "urlMain": site.get("urlMain", ""), "category": site.get("category", "Other")}
        for name, site in SITES.items()
    ]
    return jsonify(sorted(data, key=lambda x: x["name"].lower()))


@app.route("/check")
def check():
    username = request.args.get("q", "").strip()
    if not username:
        return Response('data: {"error": "No username"}\n\n', mimetype="text/event-stream")
    if not USERNAME_RE.match(username):
        return Response('data: {"error": "Invalid username"}\n\n', mimetype="text/event-stream")

    def generate():
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(check_site, name, site, username): name
                for name, site in SITES.items()
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    yield f"data: {json.dumps(result)}\n\n"
                except Exception:
                    log.exception("worker failed")
        yield 'data: {"done": true}\n\n'

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    log.info("Username Checker — %d platforms loaded", len(SITES))
    log.info("Serving on http://%s:%d", host, port)
    app.run(host=host, port=port, debug=debug, threaded=True)
