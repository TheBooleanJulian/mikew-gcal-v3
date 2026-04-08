"""
health.py — Local branded status server for TheBooleanJulian bots.

Replaces the external thebooleanjulian-bot-core git dependency.
"""

import threading
from datetime import datetime
from flask import Flask

# ─── branding constants ──────────────────────────────────────────────────────
BRAND_NAME   = "TheBooleanJulian"
BRAND_GITHUB = "https://github.com/TheBooleanJulian"
BRAND_HANDLE = "@TheBooleanJulian"

TEAL       = "#00BFA5"
BG_DARK    = "#0d1117"
TEXT_WHITE = "#e6edf3"
TEXT_MUTED = "#8b949e"


class StatusServer:
    """Lightweight Flask health-check server with TheBooleanJulian branding."""

    def __init__(
        self,
        bot_name: str,
        bot_username: str,
        bot_description: str,
        bot_version: str = "1.0.0",
        icon_emoji: str = "🤖",
        accent_color: str = TEAL,
        port: int = 8080,
    ):
        self.bot_name = bot_name
        self.bot_username = bot_username
        self.bot_description = bot_description
        self.bot_version = bot_version
        self.icon_emoji = icon_emoji
        self.accent_color = accent_color
        self.port = port
        self._metrics_fn = None

        self._app = Flask(__name__)
        self._app.add_url_rule("/healthz", "healthz", self._healthz)
        self._app.add_url_rule("/", "status", self._status_page)

    def start(self, port: int = None, metrics_callback=None):
        """Start the HTTP server in the current thread (blocking)."""
        if port is not None:
            self.port = port
        if metrics_callback is not None:
            self._metrics_fn = metrics_callback
        self._run()

    def _run(self):
        import logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)
        self._app.run(host="0.0.0.0", port=self.port)

    def _healthz(self):
        return {"status": "ok"}, 200

    def _status_page(self):
        metrics = self._metrics_fn() if self._metrics_fn else {}
        rows = "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in metrics.items()
        )
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{self.bot_name} — Status</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: {BG_DARK};
      color: {TEXT_WHITE};
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }}
    .card {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 2rem 2.5rem;
      max-width: 520px;
      width: 100%;
    }}
    .header {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }}
    .emoji {{ font-size: 2rem; }}
    h1 {{ font-size: 1.4rem; font-weight: 700; }}
    .username {{ color: {self.accent_color}; font-size: 0.9rem; margin-top: 0.1rem; }}
    p.desc {{ color: {TEXT_MUTED}; font-size: 0.9rem; margin-bottom: 1.5rem; line-height: 1.5; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    td {{ padding: 0.45rem 0.25rem; border-bottom: 1px solid #21262d; }}
    td:first-child {{ color: {TEXT_MUTED}; width: 55%; }}
    td:last-child {{ font-weight: 600; text-align: right; }}
    .footer {{
      margin-top: 1.75rem;
      padding-top: 1rem;
      border-top: 1px solid #21262d;
      color: {TEXT_MUTED};
      font-size: 0.78rem;
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.25rem;
    }}
    a {{ color: {self.accent_color}; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <span class="emoji">{self.icon_emoji}</span>
      <div>
        <h1>{self.bot_name}</h1>
        <div class="username">{self.bot_username}</div>
      </div>
    </div>
    <p class="desc">{self.bot_description}</p>
    <table>
      <tbody>
        {rows}
      </tbody>
    </table>
    <div class="footer">
      <span>v{self.bot_version}</span>
      <span>Built by <a href="{BRAND_GITHUB}" target="_blank">{BRAND_NAME}</a></span>
    </div>
  </div>
</body>
</html>"""
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}
