"""
Student Grade Notification Service - Web Dashboard
Run: python demo/myapp/app_ui.py
Open: http://localhost:5050
"""
from flask import Flask, render_template_string
import os

app = Flask(__name__)

SERVICES = [
    {"key": "PORTAL_API_KEY", "label": "Grade Portal API",     "icon": "🎓", "critical": True},
    {"key": "PORTAL_URL",     "label": "Portal Endpoint",      "icon": "🌐", "critical": True},
    {"key": "DATABASE_URL",   "label": "Student Database",     "icon": "🗄️",  "critical": True},
    {"key": "SMTP_HOST",      "label": "Email Server",         "icon": "📧", "critical": True},
    {"key": "SMTP_USER",      "label": "Email Account",        "icon": "👤", "critical": True},
    {"key": "SECRET_KEY",     "label": "Security Key",         "icon": "🔐", "critical": True},
    {"key": "LOG_LEVEL",      "label": "Log Level",            "icon": "📋", "critical": False},
    {"key": "CHECK_INTERVAL", "label": "Check Interval (sec)", "icon": "⏱️",  "critical": False},
]

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Grade Notification Service — HAW Kiel</title>
  <meta http-equiv="refresh" content="3">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, sans-serif; }
    body { background: #0f1117; color: #e2e8f0; min-height: 100vh; }

    .header { background: #1a1d2e; border-bottom: 2px solid #2d3748; padding: 20px 40px; display: flex; align-items: center; gap: 16px; }
    .header h1 { font-size: 22px; font-weight: 600; }
    .header .sub { font-size: 13px; color: #718096; }
    .status-pill { margin-left: auto; padding: 6px 18px; border-radius: 20px; font-size: 13px; font-weight: 600; }
    .pill-ok  { background: #1a4731; color: #48bb78; border: 1px solid #276749; }
    .pill-err { background: #742a2a; color: #fc8181; border: 1px solid #9b2c2c; }

    .main { padding: 32px 40px; }
    .section-title { font-size: 12px; color: #4a5568; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 14px; }

    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-bottom: 32px; }

    .card { background: #1a1d2e; border-radius: 10px; padding: 18px 20px; border: 1px solid #2d3748; display: flex; align-items: center; gap: 14px; }
    .card.ok   { border-left: 4px solid #276749; }
    .card.err  { border-left: 4px solid #9b2c2c; }
    .card.warn { border-left: 4px solid #975a16; }
    .card-icon { font-size: 24px; }
    .card-info { flex: 1; }
    .card-label { font-size: 14px; font-weight: 500; color: #e2e8f0; }
    .card-value { font-size: 12px; color: #718096; margin-top: 3px; font-family: monospace; }
    .card-badge { font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 10px; }
    .badge-ok   { background: #1a4731; color: #68d391; }
    .badge-err  { background: #742a2a; color: #fc8181; }
    .badge-warn { background: #744210; color: #f6ad55; }

    .summary { background: #1a1d2e; border-radius: 10px; padding: 20px 24px; border: 1px solid #2d3748; display: flex; gap: 32px; align-items: center; }
    .stat { text-align: center; }
    .stat-num { font-size: 32px; font-weight: 700; }
    .stat-lbl { font-size: 11px; color: #4a5568; text-transform: uppercase; margin-top: 2px; }
    .num-ok  { color: #48bb78; }
    .num-err { color: #fc8181; }
    .num-warn{ color: #f6ad55; }

    .drift-box { border-radius: 10px; padding: 16px 24px; margin-left: auto; text-align: center; min-width: 180px; border: 2px solid; }
    .drift-NONE   { background:#1a2e1a; border-color:#276749; }
    .drift-LOW    { background:#2d2a12; border-color:#975a16; }
    .drift-MEDIUM { background:#2d1f08; border-color:#c05621; }
    .drift-HIGH   { background:#2d1010; border-color:#9b2c2c; }
    .drift-label  { font-size: 26px; font-weight: 700; letter-spacing: 2px; }
    .drift-NONE   .drift-label { color:#68d391; }
    .drift-LOW    .drift-label { color:#f6e05e; }
    .drift-MEDIUM .drift-label { color:#f6ad55; }
    .drift-HIGH   .drift-label { color:#fc8181; }
    .drift-sub { font-size: 12px; color:#718096; margin-top:4px; }

    .hint { font-size: 12px; color: #4a5568; margin-top: 20px; text-align: center; }
  </style>
</head>
<body>
<div class="header">
  <span style="font-size:28px">🎓</span>
  <div>
    <h1>Grade Notification Service</h1>
    <div class="sub">HAW Kiel — Student Portal Integration</div>
  </div>
  {% if all_critical_ok %}
    <span class="status-pill pill-ok">● SERVICE RUNNING</span>
  {% else %}
    <span class="status-pill pill-err">● SERVICE FAILED</span>
  {% endif %}
</div>

<div class="main">
  <div class="section-title">Service Configuration Status</div>
  <div class="grid">
    {% for s in services %}
    <div class="card {{ s.state }}">
      <div class="card-icon">{{ s.icon }}</div>
      <div class="card-info">
        <div class="card-label">{{ s.label }}</div>
        <div class="card-value">{{ s.display }}</div>
      </div>
      <span class="card-badge badge-{{ s.state }}">
        {% if s.state == 'ok' %}CONNECTED
        {% elif s.state == 'err' %}MISSING
        {% else %}DEFAULT{% endif %}
      </span>
    </div>
    {% endfor %}
  </div>

  <div class="summary">
    <div class="stat"><div class="stat-num num-ok">{{ ok_count }}</div><div class="stat-lbl">Connected</div></div>
    <div class="stat"><div class="stat-num num-err">{{ err_count }}</div><div class="stat-lbl">Missing Critical</div></div>
    <div class="stat"><div class="stat-num num-warn">{{ warn_count }}</div><div class="stat-lbl">Warning</div></div>
    <div class="drift-box drift-{{ drift_level }}">
      <div class="drift-label">{{ drift_level }}</div>
      <div class="drift-sub">Drift Score: {{ drift_score }}</div>
    </div>
  </div>
  <div class="hint">Page auto-refreshes every 3 seconds — edit your .env and see changes live</div>
</div>
</body>
</html>
"""

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", ".env")
    vals = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals

@app.route("/")
def index():
    env = load_env()
    services = []
    ok_count = err_count = warn_count = 0
    score = 0

    for s in SERVICES:
        val = env.get(s["key"], os.environ.get(s["key"], ""))
        if val:
            state = "ok"
            display = val if len(val) < 35 else val[:32] + "..."
            ok_count += 1
        else:
            display = "NOT SET"
            if s["critical"]:
                state = "err"
                err_count += 1
                score += 3
            else:
                state = "warn"
                warn_count += 1
                score += 1

        services.append({**s, "state": state, "display": display})

    if score == 0:       drift_level = "NONE"
    elif score <= 3:     drift_level = "LOW"
    elif score <= 9:     drift_level = "MEDIUM"
    else:                drift_level = "HIGH"

    return render_template_string(HTML,
        services=services,
        ok_count=ok_count,
        err_count=err_count,
        warn_count=warn_count,
        drift_level=drift_level,
        drift_score=score,
        all_critical_ok=(err_count == 0)
    )

if __name__ == "__main__":
    print("\n  Grade Notification Service UI")
    print("  Open browser at: http://localhost:5050\n")
    app.run(port=5050, debug=False)
