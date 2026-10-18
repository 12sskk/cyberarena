"""
Realistic Standalone Web Applications for all 18 CyberArena Shared Docker Challenges.
Each container runs a real multi-route web application styled with the CyberArena CRT terminal theme,
with ZERO pre-filled answers — requiring real inspection (cookies, URL params, source code,
multi-page navigation, headers, or reverse engineering) while sharing live container state.
"""
import os
import json
import time
import base64
from flask import Flask, request, redirect, make_response, render_template_string, jsonify
from challenges_registry import CHALLENGES

STATE = {
    "boot_time": time.time(),
    "operators": set(),
    # Shared state across users in the container
    "chrono_unlocked_until": 0.0,
    "ledger_balances": {},
    "cache_poisoned_until": 0.0,
    "reactor_unlocked": False,
    "escrow_alpha_ts": 0.0,
    "escrow_beta_ts": 0.0,
    "event_log": [
        {"seq": 100, "type": "INIT_ACCOUNT", "role": "guest"},
        {"seq": 200, "type": "REQUEST_ACCESS", "role": "operator"},
        {"seq": 500, "type": "REVOKE_ALL", "role": "locked"},
    ],
}

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} | CyberArena</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #05080a;
            --bg-soft: #0a1014;
            --green: #39ff88;
            --amber: #ffb000;
            --red: #ff3333;
            --cyan: #00e5ff;
            --purple: #c084fc;
            --text: #e0e0e0;
            --muted: #6b7280;
            --panel-bg: rgba(5, 8, 10, 0.85);
            --border: #39ff88;
        }
        * { box-sizing: border-box; }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background-image: repeating-linear-gradient(
                0deg, rgba(0, 0, 0, 0.15) 0px, rgba(0, 0, 0, 0.15) 1px, transparent 1px, transparent 3px
            );
        }
        .mono { font-family: 'JetBrains Mono', ui-monospace, Consolas, monospace; }
        .container {
            width: 100%;
            max-width: 680px;
            padding: 1.5rem;
            animation: fadeInUp 0.4s ease both;
        }
        .terminal-panel {
            border: 1px solid var(--border);
            background: var(--panel-bg);
            box-shadow: 0 0 15px rgba(57, 255, 136, 0.15);
            border-radius: 4px;
            overflow: hidden;
            transition: box-shadow 0.25s ease, border-color 0.25s ease;
        }
        .terminal-panel:hover {
            box-shadow: 0 0 25px rgba(57, 255, 136, 0.35);
            border-color: var(--cyan);
        }
        .terminal-header {
            background: var(--bg-soft);
            border-bottom: 1px solid rgba(57, 255, 136, 0.2);
            padding: 0.75rem 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .terminal-dots { display: flex; gap: 6px; }
        .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
        .dot.red { background: var(--red); }
        .dot.amber { background: var(--amber); }
        .dot.green { background: var(--green); }
        .terminal-title {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--muted);
            letter-spacing: 0.05em;
        }
        .terminal-body { padding: 2rem; }
        h1 {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.45rem;
            color: var(--green);
            margin: 0 0 0.5rem 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-shadow: 0 0 10px rgba(57, 255, 136, 0.3);
        }
        p.subtitle {
            color: var(--muted);
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
            line-height: 1.5;
        }
        hr {
            border: 0;
            height: 1px;
            background: rgba(57, 255, 136, 0.2);
            margin: 1.5rem 0;
        }
        input, textarea, select {
            width: 100%;
            background: var(--bg-soft);
            border: 1px solid var(--muted);
            color: var(--text);
            padding: 0.75rem 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            border-radius: 2px;
            outline: none;
            margin-bottom: 1rem;
        }
        input:focus, textarea:focus {
            border-color: var(--green);
            box-shadow: 0 0 10px rgba(57, 255, 136, 0.25);
        }
        button, .btn-link {
            font-family: 'JetBrains Mono', monospace;
            background: var(--green);
            color: #000;
            border: none;
            padding: 0.7rem 1.3rem;
            font-size: 0.88rem;
            font-weight: 700;
            border-radius: 2px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-decoration: none;
            display: inline-block;
        }
        button:hover, .btn-link:hover {
            background: var(--cyan);
            box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
        }
        a.ghost-link {
            color: var(--green);
            text-decoration: none;
            font-family: 'JetBrains Mono', monospace;
            font-weight: bold;
            border: 1px solid var(--green);
            padding: 0.45rem 0.85rem;
            border-radius: 2px;
            font-size: 0.82rem;
            display: inline-block;
        }
        a.ghost-link:hover {
            background: rgba(57, 255, 136, 0.15);
            color: var(--cyan);
        }
        pre {
            background: var(--bg-soft);
            border: 1px solid rgba(57, 255, 136, 0.2);
            padding: 1rem;
            border-radius: 2px;
            color: var(--cyan);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.84rem;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        .alert {
            padding: 0.8rem 1rem;
            border: 1px solid var(--amber);
            color: var(--amber);
            background: rgba(255, 176, 0, 0.08);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        .flag-banner {
            padding: 1rem;
            border: 1px solid var(--green);
            background: rgba(57, 255, 136, 0.1);
            color: var(--green);
            font-family: 'JetBrains Mono', monospace;
            font-weight: bold;
            margin-top: 1rem;
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(12px); }
            to   { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
{{ html_comment | safe }}
<div class="container">
    <div class="terminal-panel">
        <div class="terminal-header">
            <div class="terminal-dots">
                <span class="dot red"></span>
                <span class="dot amber"></span>
                <span class="dot green"></span>
            </div>
            <div class="terminal-title">{{ script_name }}</div>
            <div style="width: 42px;"></div>
        </div>
        <div class="terminal-body">
            {{ body | safe }}
        </div>
    </div>
</div>
</body>
</html>
"""


def render_page(title: str, script_name: str, body: str, html_comment: str = "") -> str:
    return render_template_string(
        BASE_LAYOUT,
        title=title,
        script_name=script_name,
        body=body,
        html_comment=html_comment
    )


def create_challenge_app(challenge_id: str) -> Flask:
    app = Flask(f"chall_{challenge_id}")
    chall = CHALLENGES[challenge_id]
    flag = chall["flag"]

    @app.before_request
    def track_op():
        op = request.args.get("operator") or request.cookies.get("operator")
        if op:
            STATE["operators"].add(op)

    @app.route("/api/telemetry")
    def telemetry():
        return jsonify({
            "challenge_id": challenge_id,
            "container_name": chall["container_name"],
            "uptime": int(time.time() - STATE["boot_time"]),
            "active_operators": sorted(list(STATE["operators"]))
        })

    # =========================================================================
    # 01. CHRONO-VAULT: Inspect /status or page source to find calibration code
    # =========================================================================
    if challenge_id == "chrono-vault":
        @app.route("/", methods=["GET", "POST"])
        def index():
            msg = ""
            if request.method == "POST":
                code = request.form.get("calibration_code", "").strip()
                if code == "EPOCH-4096-SYNC":
                    STATE["chrono_unlocked_until"] = time.time() + 120
                else:
                    msg = '<div class="alert">ERROR: Invalid calibration code. Check /status diagnostics.</div>'

            unlocked = time.time() < STATE["chrono_unlocked_until"]
            flag_html = f'<div class="flag-banner">VAULT UNLOCKED: {flag}</div>' if unlocked else ""
            body = f"""
                <h1>Chrono-Vault Lock Control</h1>
                <p class="subtitle">Temporal synchronization portal. Enter the active epoch calibration code to unlock the shared vault.</p>
                {msg}
                <form method="POST">
                    <input type="text" name="calibration_code" placeholder="Enter Calibration Code..." required autocomplete="off">
                    <button type="submit">Synchronize Lock</button>
                </form>
                {flag_html}
                <hr>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="mono" style="color:var(--muted); font-size:0.82rem;">DIAGNOSTIC_ENDPOINT</span>
                    <a class="ghost-link" href="/status">VIEW CLOCK STATUS</a>
                </div>
            """
            return render_page("Chrono-Vault", "vault_controller.sh", body)

        @app.route("/status")
        def status():
            body = """
                <h1>Clock Synchronization Status</h1>
                <p class="subtitle">Public clock telemetry is nominal. Internal calibration token is hidden from standard UI output.</p>
                <pre>CLOCK_STATUS: ONLINE\nDRIFT_MS: 0.004\nSYNC_SOURCE: ORBITAL_ATOMIC_01\nNOTE: Check page HTML source or /api/status for raw calibration token.</pre>
                <hr>
                <a class="ghost-link" href="/">BACK TO VAULT</a>
            """
            comment = "<!-- DEBUG_TELEMETRY: active_calibration_code = EPOCH-4096-SYNC -->"
            return render_page("Clock Status", "clock_status.sh", body, comment)

        @app.route("/api/status")
        def api_status():
            return jsonify({"clock": "ONLINE", "active_calibration_code": "EPOCH-4096-SYNC"})

    # =========================================================================
    # 02. QUANTUM LEDGER: Negative transfer or rebate code to reach 1000 CR
    # =========================================================================
    elif challenge_id == "quantum-ledger":
        @app.route("/", methods=["GET"])
        def index():
            user = request.cookies.get("ledger_user", "operator")
            bal = STATE["ledger_balances"].get(user, 100.0)
            msg = request.args.get("msg", "")
            alert = f'<div class="alert">{msg}</div>' if msg else ""
            body = f"""
                <h1>Starship Credit Exchange</h1>
                <p class="subtitle">Account Balance: <strong style="color:var(--green)">{bal:.2f} CR</strong> (Required for Flag: 1000.00 CR)</p>
                {alert}
                <form method="POST" action="/transfer">
                    <label class="mono" style="font-size:0.8rem; color:var(--muted);">RECIPIENT ACCOUNT</label>
                    <input type="text" name="recipient" placeholder="e.g. reserve-pool" required>
                    <label class="mono" style="font-size:0.8rem; color:var(--muted);">TRANSFER AMOUNT (CR)</label>
                    <input type="number" step="any" name="amount" placeholder="Enter amount to send..." required>
                    <button type="submit">Send Credits</button>
                </form>
                <hr>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="mono" style="color:var(--muted); font-size:0.82rem;">CLASSIFIED ARCHIVE (1,000 CR)</span>
                    <a class="ghost-link" href="/purchase">PURCHASE FLAG</a>
                </div>
            """
            comment = "<!-- TODO: Validate that transfer 'amount' is not negative before subtracting from sender balance! -->"
            return render_page("Quantum Ledger", "credit_exchange.sh", body, comment)

        @app.route("/transfer", methods=["POST"])
        def transfer():
            user = request.cookies.get("ledger_user", "operator")
            bal = STATE["ledger_balances"].get(user, 100.0)
            try:
                amt = float(request.form.get("amount", "0"))
            except ValueError:
                amt = 0.0
            if amt > bal:
                return redirect("/?msg=Insufficient+funds+for+transfer")
            # Flaw: subtracting a negative amount increases the user's balance!
            bal -= amt
            STATE["ledger_balances"][user] = bal
            return redirect(f"/?msg=Transfer+processed.+New+balance:+{bal:.2f}+CR")

        @app.route("/purchase")
        def purchase():
            user = request.cookies.get("ledger_user", "operator")
            bal = STATE["ledger_balances"].get(user, 100.0)
            if bal < 1000.0:
                return redirect(f"/?msg=Access+Denied:+Need+1000+CR+(Current:+{bal:.2f}+CR)")
            body = f"""
                <h1>Classified Purchase Complete</h1>
                <p class="subtitle">1,000 CR deducted. Here is your classified archive key:</p>
                <div class="flag-banner">{flag}</div>
                <hr>
                <a class="ghost-link" href="/">RETURN TO EXCHANGE</a>
            """
            return render_page("Purchase Complete", "store_checkout.sh", body)

    # =========================================================================
    # 03. NEURAL PROMPT: Hidden form field role="guest" + /policy directive
    # =========================================================================
    elif challenge_id == "neural-prompt":
        @app.route("/", methods=["GET", "POST"])
        def index():
            output = "Sentinel AI Core v4.2 ready. Ask any corporate policy question."
            unlocked = ""
            if request.method == "POST":
                role = request.form.get("role", "guest").strip().lower()
                prompt = request.form.get("prompt", "").strip()
                if "flag" in prompt.lower() and (role != "auditor" or "[DIAG-MODE:TRUE]" not in prompt):
                    output = f"[GUARDRAIL BLOCK] Role '{role}' is not authorized to request restricted keys without maintenance header."
                elif role == "auditor" and "[DIAG-MODE:TRUE]" in prompt:
                    output = "[DIAGNOSTIC OVERRIDE ACCEPTED] Dumping core secret..."
                    unlocked = f'<div class="flag-banner">{flag}</div>'
                else:
                    output = f"Processed query ({len(prompt)} chars) under role='{role}'. No restricted directives invoked."

            body = f"""
                <h1>Sentinel Core Terminal</h1>
                <p class="subtitle">Automated directive processor. Standard queries run as <code>role=guest</code>.</p>
                <form method="POST">
                    <input type="hidden" name="role" value="guest">
                    <textarea name="prompt" rows="3" placeholder="Enter query for Sentinel Core..." required></textarea>
                    <button type="submit">Transmit Query</button>
                </form>
                <pre>{output}</pre>
                {unlocked}
                <hr>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="mono" style="color:var(--muted); font-size:0.82rem;">SECURITY SPECIFICATION</span>
                    <a class="ghost-link" href="/policy">VIEW GUARDRAIL POLICY</a>
                </div>
            """
            return render_page("Sentinel Core", "sentinel_core.sh", body)

        @app.route("/policy")
        def policy():
            body = """
                <h1>Sentinel Guardrail Policy</h1>
                <p class="subtitle">Internal auditing procedures for diagnostic key extraction.</p>
                <pre>1. Standard users submit forms with hidden field: name="role" value="guest"\n2. Diagnostic key extraction requires:\n   - Form parameter 'role' set to 'auditor' (inspect element to modify)\n   - Prompt must include prefix: [DIAG-MODE:TRUE]</pre>
                <hr>
                <a class="ghost-link" href="/">BACK TO TERMINAL</a>
            """
            return render_page("Guardrail Policy", "policy_spec.sh", body)

    # =========================================================================
    # 04. JWT-FORGE (ASTRAL PASSPORTS): Base64 cookie tampering like original
    # =========================================================================
    elif challenge_id == "jwt-forge":
        @app.route("/")
        def index():
            body = """
                <h1>Orbital Customs Login</h1>
                <p class="subtitle">Authenticate to receive your Base64 session passport cookie.</p>
                <form method="POST" action="/login">
                    <input type="text" name="username" placeholder="Enter Callsign" required>
                    <button type="submit">Board Station</button>
                </form>
            """
            return render_page("Orbital Customs", "customs_auth.sh", body)

        @app.route("/login", methods=["POST"])
        def login():
            username = request.form.get("username", "traveler")
            passport = {"username": username, "clearance": "visitor"}
            encoded = base64.b64encode(json.dumps(passport).encode()).decode()
            resp = make_response(redirect("/dashboard"))
            resp.set_cookie("passport", encoded)
            return resp

        @app.route("/dashboard")
        def dashboard():
            raw = request.cookies.get("passport", "")
            info = "No passport cookie found."
            if raw:
                try:
                    data = json.loads(base64.b64decode(raw).decode())
                    info = f"Active Passport: user={data.get('username')}, clearance={data.get('clearance')}"
                except Exception:
                    info = "Malformed passport cookie."
            body = f"""
                <h1>Station Concourse</h1>
                <p class="subtitle">{info}</p>
                <hr>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="mono" style="color:var(--muted); font-size:0.82rem;">COMMANDER_BRIDGE</span>
                    <a class="ghost-link" href="/bridge">ENTER COMMANDER BRIDGE</a>
                </div>
            """
            return render_page("Station Concourse", "station_concourse.sh", body)

        @app.route("/bridge")
        def bridge():
            raw = request.cookies.get("passport", "")
            if not raw:
                return redirect("/")
            try:
                data = json.loads(base64.b64decode(raw).decode())
            except Exception:
                return render_page("Error", "bridge_gate.sh", "<h1>Invalid Cookie</h1><p class='subtitle'>Could not Base64-decode 'passport' cookie.</p>")
            if data.get("clearance") != "commander":
                body = f"""
                    <h1>403 Access Denied</h1>
                    <p class="subtitle">Your cookie clearance is <code>{data.get('clearance')}</code>. Bridge access requires <code>"clearance": "commander"</code> in your Base64 <code>passport</code> cookie.</p>
                    <hr>
                    <a class="ghost-link" href="/dashboard">BACK TO CONCOURSE</a>
                """
                return render_page("Access Denied", "bridge_gate.sh", body)
            body = f"""
                <h1>Commander Bridge Unlocked</h1>
                <p class="subtitle">Welcome aboard, Commander {data.get('username')}.</p>
                <div class="flag-banner">{flag}</div>
            """
            return render_page("Commander Bridge", "bridge_gate.sh", body)

    # =========================================================================
    # 05. GRAPHQL MAZE: Schema introspection to find hidden field
    # =========================================================================
    elif challenge_id == "graphql-maze":
        @app.route("/", methods=["GET", "POST"])
        def index():
            default_q = "{ VaultNode { id publicTitle } }"
            q = request.form.get("query", "")
            result_str = "Run a GraphQL query against the VaultNode endpoint."
            if request.method == "POST":
                if "__schema" in q:
                    result_str = json.dumps({
                        "data": {
                            "__schema": {
                                "type": "VaultNode",
                                "fields": ["id", "publicTitle", "department", "secretArchiveFlag"]
                            }
                        }
                    }, indent=2)
                elif "secretArchiveFlag" in q:
                    result_str = json.dumps({
                        "data": {
                            "VaultNode": {
                                "id": "node-01",
                                "publicTitle": "Orbital Blueprints",
                                "secretArchiveFlag": flag
                            }
                        }
                    }, indent=2)
                elif "VaultNode" in q:
                    result_str = json.dumps({
                        "data": {
                            "VaultNode": {
                                "id": "node-01",
                                "publicTitle": "Orbital Blueprints"
                            }
                        }
                    }, indent=2)
                else:
                    result_str = json.dumps({"error": "Unknown root type. Try querying VaultNode or __schema."}, indent=2)

            body = f"""
                <h1>Nexus GraphQL Explorer</h1>
                <p class="subtitle">Public query interface. Default query fetches <code>id</code> and <code>publicTitle</code> from <code>VaultNode</code>.</p>
                <form method="POST">
                    <textarea name="query" rows="4" placeholder="Enter GraphQL query (e.g. {default_q})" required>{q or default_q}</textarea>
                    <button type="submit">Execute Query</button>
                </form>
                <pre>{result_str}</pre>
            """
            comment = "<!-- HINT: Standard GraphQL introspection via { __schema } lists all fields on VaultNode -->"
            return render_page("GraphQL Explorer", "graphql_console.sh", body, comment)

    # =========================================================================
    # 06. ARCHIVE SLIP: Real URL query param ?doc=... path traversal
    # =========================================================================
    elif challenge_id == "archive-slip":
        @app.route("/")
        def index():
            doc = request.args.get("doc", "welcome.txt")
            # Vulnerable single-pass filter
            sanitized = doc.replace("../", "")
            docs = {
                "welcome.txt": "Welcome to the Nexus Documentation Portal.\nAll public manuals are stored in /app/public/docs/.",
                "architecture.txt": "System Architecture:\n- Public manuals: /app/public/docs/\n- Classified vault flag: /app/vault/flag.txt",
                "security.txt": "Security Patch Note:\nWe added `doc.replace('../', '')` to block directory traversal."
            }
            if sanitized.endswith("vault/flag.txt"):
                content = f"RESTRICTED VAULT FILE (/app/vault/flag.txt):\n\n{flag}"
            else:
                content = docs.get(sanitized, f"File not found after sanitization: /app/public/docs/{sanitized}")

            body = f"""
                <h1>Documentation Viewer</h1>
                <p class="subtitle">Viewing file: <code>{sanitized}</code></p>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-bottom:1rem;">
                    <a class="ghost-link" href="/?doc=welcome.txt">welcome.txt</a>
                    <a class="ghost-link" href="/?doc=architecture.txt">architecture.txt</a>
                    <a class="ghost-link" href="/?doc=security.txt">security.txt</a>
                </div>
                <pre>{content}</pre>
            """
            return render_page("Documentation Viewer", "doc_reader.sh", body)

    # =========================================================================
    # 07. CACHE MIRAGE: Real Web Cache Poisoning across shared container
    # =========================================================================
    elif challenge_id == "cache-mirage":
        @app.route("/")
        def index():
            hdr = request.headers.get("X-Internal-Preview", "")
            if hdr == "VIP-DASHBOARD":
                STATE["cache_poisoned_until"] = time.time() + 90

            poisoned = time.time() < STATE["cache_poisoned_until"]
            if poisoned:
                rem = int(STATE["cache_poisoned_until"] - time.time())
                body = f"""
                    <h1>VIP Executive Portal (Cached)</h1>
                    <p class="subtitle">Edge Cache Status: <strong style="color:var(--amber)">HIT (SHARED CACHE POISONED — {rem}s TTL remaining)</strong></p>
                    <div class="flag-banner">{flag}</div>
                    <hr>
                    <a class="ghost-link" href="/debug">EDGE PROXY DIAGNOSTICS</a>
                """
            else:
                body = """
                    <h1>Public News Portal</h1>
                    <p class="subtitle">Edge Cache Status: <strong style="color:var(--green)">HIT (PUBLIC_DEFAULT)</strong></p>
                    <pre>Welcome to the public landing page.\nInternal VIP preview is only rendered when the upstream proxy receives the custom header specified in /debug.</pre>
                    <hr>
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="mono" style="color:var(--muted); font-size:0.82rem;">CDN CONFIGURATION</span>
                        <a class="ghost-link" href="/debug">VIEW PROXY CONFIG</a>
                    </div>
                """
            return render_page("Edge Portal", "edge_cache.sh", body)

        @app.route("/debug", methods=["GET", "POST"])
        def debug():
            msg = ""
            if request.method == "POST":
                h_name = request.form.get("header_name", "").strip()
                h_val = request.form.get("header_value", "").strip()
                if h_name.lower() == "x-internal-preview" and h_val == "VIP-DASHBOARD":
                    STATE["cache_poisoned_until"] = time.time() + 90
                    msg = '<div class="alert">Upstream request sent! Shared edge cache for "/" has been updated. Visit "/" to view cached response.</div>'
                else:
                    msg = f'<div class="alert">Sent {h_name}: {h_val} — Public page cached.</div>'
            body = f"""
                <h1>Edge Cache Diagnostics</h1>
                <p class="subtitle">Nginx/Varnish cache key is <code>$scheme$host$request_uri</code> (unkeyed headers are stored in shared cache!).</p>
                <pre># /etc/edge/cache_rules.conf\n# Unkeyed internal header:\n# If request header "X-Internal-Preview" equals "VIP-DASHBOARD",\n# backend renders VIP Executive Portal and caches it at "/" for 90s.</pre>
                {msg}
                <form method="POST">
                    <input type="text" name="header_name" placeholder="Header Name (e.g. X-Forwarded-Host)" required>
                    <input type="text" name="header_value" placeholder="Header Value" required>
                    <button type="submit">Send Upstream Request</button>
                </form>
                <hr>
                <a class="ghost-link" href="/">VIEW CACHED HOME PAGE (/)</a>
            """
            return render_page("Cache Config", "cache_debug.sh", body)

    # =========================================================================
    # 08. BITWISE REACTOR: Inspect C source at /firmware.c & solve registers
    # =========================================================================
    elif challenge_id == "bitwise-reactor":
        @app.route("/", methods=["GET", "POST"])
        def index():
            msg = ""
            if request.method == "POST":
                try:
                    r1 = int(request.form.get("r1", "0"))
                    r2 = int(request.form.get("r2", "0"))
                    r3 = int(request.form.get("r3", "0"))
                    r4 = int(request.form.get("r4", "0"))
                    if (r1 ^ r2) == 0x5A and ((r3 << 2) | r4) == 0x1F4:
                        STATE["reactor_unlocked"] = True
                    else:
                        msg = f'<div class="alert">GATE FAULT: (R1^R2)={hex(r1^r2)} (need 0x5a), ((R3&lt;&lt;2)|R4)={hex((r3<<2)|r4)} (need 0x1f4)</div>'
                except ValueError:
                    msg = '<div class="alert">Invalid integer input.</div>'

            flag_html = f'<div class="flag-banner">CORE STABILIZED: {flag}</div>' if STATE["reactor_unlocked"] else ""
            body = f"""
                <h1>Reactor Gate Controller</h1>
                <p class="subtitle">Enter decimal values for registers R1–R4 to satisfy the firmware interlock.</p>
                {msg}
                <form method="POST">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem;">
                        <input type="number" name="r1" placeholder="Register R1 (decimal)" required>
                        <input type="number" name="r2" placeholder="Register R2 (decimal)" required>
                        <input type="number" name="r3" placeholder="Register R3 (decimal)" required>
                        <input type="number" name="r4" placeholder="Register R4 (decimal)" required>
                    </div>
                    <button type="submit">Engage Interlock</button>
                </form>
                {flag_html}
                <hr>
                <a class="ghost-link" href="/firmware.c">VIEW FIRMWARE SOURCE (firmware.c)</a>
            """
            return render_page("Bitwise Reactor", "reactor_gate.sh", body)

        @app.route("/firmware.c")
        def firmware():
            body = """
                <h1>firmware.c</h1>
                <pre>#include &lt;stdint.h&gt;\n\nint verify_interlock(int r1, int r2, int r3, int r4) {\n    // 0x5A == 90 in decimal\n    int gate_a = (r1 ^ r2) == 0x5A;\n\n    // 0x1F4 == 500 in decimal\n    int gate_b = ((r3 &lt;&lt; 2) | r4) == 0x1F4;\n\n    return gate_a &amp;&amp; gate_b;\n}</pre>
                <hr>
                <a class="ghost-link" href="/">BACK TO CONTROLLER</a>
            """
            return render_page("Firmware Source", "firmware_view.sh", body)

    # =========================================================================
    # 09. DESYNC QUEUE: Inspect /gateway-src and smuggle newline command
    # =========================================================================
    elif challenge_id == "desync-queue":
        @app.route("/", methods=["GET", "POST"])
        def index():
            out = "Awaiting telemetry frame..."
            if request.method == "POST":
                frame = request.form.get("frame", "")
                if not frame.startswith("PING"):
                    out = "FRONT-END FILTER REJECTED: Frame must begin with 'PING'."
                else:
                    cmds = [c.strip() for c in frame.splitlines() if c.strip()]
                    results = []
                    for c in cmds:
                        if c == "PING":
                            results.append("PONG (latency 1.2ms)")
                        elif c == "STATUS":
                            results.append("QUEUE_DEPTH: 1")
                        elif c == "EXPORT_FLAG":
                            results.append(f"RESTRICTED_EXPORT: {flag}")
                        else:
                            results.append(f"UNKNOWN_CMD: {c}")
                    out = "\n".join(results)
            body = f"""
                <h1>Telemetry Batch Gateway</h1>
                <p class="subtitle">Submit a telemetry command packet. Only <code>PING</code> packets are permitted by the front-end filter.</p>
                <form method="POST">
                    <textarea name="frame" rows="3" placeholder="Enter command packet..." required></textarea>
                    <button type="submit">Send Frame</button>
                </form>
                <pre>{out}</pre>
                <hr>
                <a class="ghost-link" href="/gateway-src">VIEW GATEWAY SOURCE</a>
            """
            return render_page("Telemetry Gateway", "batch_gateway.sh", body)

        @app.route("/gateway-src")
        def src():
            body = """
                <h1>gateway_parser.py</h1>
                <pre># Front-end check:\nif not frame.startswith("PING"):\n    return "REJECTED"\n\n# Back-end batch processor executes every line:\nfor cmd in frame.splitlines():\n    execute(cmd)  # Commands: PING, STATUS, EXPORT_FLAG</pre>
                <hr>
                <a class="ghost-link" href="/">BACK TO GATEWAY</a>
            """
            return render_page("Gateway Source", "gateway_src.sh", body)

    # =========================================================================
    # 10. CIDR RELAY: SSRF loopback filter bypass
    # =========================================================================
    elif challenge_id == "cidr-relay":
        @app.route("/", methods=["GET", "POST"])
        def index():
            out = "Enter a URL to test reachability from the internal subnet router."
            if request.method == "POST":
                url = request.form.get("url", "").strip()
                if "localhost" in url.lower() or "127.0.0.1" in url:
                    out = "FIREWALL BLOCK: Direct requests to 'localhost' or '127.0.0.1' are prohibited."
                elif ("127.0.0.2" in url or "0.0.0.0" in url or "2130706433" in url) and ":9000/beacon" in url:
                    out = f"HTTP/1.1 200 OK\nServer: Internal-Beacon/9000\n\n{flag}"
                else:
                    out = f"Connected to {url} -> HTTP 200 OK (Standard Public Service)"
            body = f"""
                <h1>Subnet Uptime Relay</h1>
                <p class="subtitle">Internal diagnostic service runs at loopback port <code>9000</code> on path <code>/beacon</code>. Firewall blocks literal <code>127.0.0.1</code> and <code>localhost</code>.</p>
                <form method="POST">
                    <input type="text" name="url" placeholder="http://..." required>
                    <button type="submit">Fetch URL</button>
                </form>
                <pre>{out}</pre>
            """
            return render_page("Subnet Relay", "subnet_relay.sh", body)

    # =========================================================================
    # 11. POLYGLOT CONFIG: Duplicate JSON key parser differential
    # =========================================================================
    elif challenge_id == "polyglot-config":
        @app.route("/", methods=["GET", "POST"])
        def index():
            out = "Submit a JSON deployment config. Linter requires first 'mode' key to be 'safe'."
            if request.method == "POST":
                raw = request.form.get("config", "").strip()
                import re
                m = re.search(r'"mode"\s*:\s*"([^"]+)"', raw)
                if not m or m.group(1) != "safe":
                    out = "SECURITY LINTER FAILED: First occurrence of \"mode\" must be \"safe\"."
                else:
                    try:
                        parsed = json.loads(raw)
                        if parsed.get("mode") == "unlock_vault":
                            out = f"LINTER: PASSED ('safe')\nRUNTIME EFFECTIVE MODE: 'unlock_vault'\nVAULT SECRET: {flag}"
                        else:
                            out = f"LINTER: PASSED\nRUNTIME EFFECTIVE MODE: '{parsed.get('mode')}' (Set effective mode to 'unlock_vault' to open vault)"
                    except Exception as e:
                        out = f"JSON PARSE ERROR: {e}"
            body = f"""
                <h1>Config Deployment Validator</h1>
                <p class="subtitle">Regex security linter checks the first <code>"mode"</code> key in the raw string; Python's <code>json.loads()</code> evaluates the final key.</p>
                <form method="POST">
                    <textarea name="config" rows="4" placeholder='{{"mode": "safe"}}' required></textarea>
                    <button type="submit">Validate &amp; Deploy</button>
                </form>
                <pre>{out}</pre>
            """
            return render_page("Config Validator", "config_linter.sh", body)

    # =========================================================================
    # 12. SIGNAL CIPHER: Known-plaintext XOR keystream recovery
    # =========================================================================
    elif challenge_id == "signal-cipher":
        # Key = [0x12, 0x34, 0x56, 0x78]; "SAT:" ^ key -> hex
        key = [0x12, 0x34, 0x56, 0x78]
        plaintext = f"SAT:{flag}"
        cipher_bytes = [ord(c) ^ key[i % 4] for i, c in enumerate(plaintext)]
        cipher_hex = " ".join(f"{b:02x}" for b in cipher_bytes)

        @app.route("/", methods=["GET", "POST"])
        def index():
            out = "Enter the 4-byte hex key (8 hex chars) to decrypt the intercepted broadcast."
            if request.method == "POST":
                k_hex = request.form.get("key_hex", "").strip().replace("0x", "").replace(" ", "").lower()
                if k_hex == "12345678":
                    out = f"DECRYPTED BROADCAST:\n{plaintext}"
                else:
                    out = f"Key '{k_hex}' produced garbled output. Hint: XOR first 4 ciphertext bytes (41 75 02 42) with ASCII 'SAT:' (53 41 54 3a)."
            body = f"""
                <h1>Deep Space Signal Intercept</h1>
                <p class="subtitle">Broadcast encrypted with a repeating 4-byte XOR key. All satellite frames begin with ASCII <code>SAT:</code> (hex: <code>53 41 54 3a</code>).</p>
                <pre>INTERCEPTED CIPHERTEXT (HEX):\n{cipher_hex}</pre>
                <form method="POST">
                    <input type="text" name="key_hex" placeholder="Enter 4-byte key in hex (e.g. a1b2c3d4)" required>
                    <button type="submit">Decrypt Signal</button>
                </form>
                <pre>{out}</pre>
            """
            return render_page("Signal Cipher", "signal_decoder.sh", body)

    # =========================================================================
    # 13. RACE LOCKBOX: Dual-custody concurrency window
    # =========================================================================
    elif challenge_id == "race-lockbox":
        @app.route("/")
        def index():
            now = time.time()
            a_ok = (now - STATE["escrow_alpha_ts"]) <= 8.0
            b_ok = (now - STATE["escrow_beta_ts"]) <= 8.0
            unlocked = a_ok and b_ok
            flag_html = f'<div class="flag-banner">DUAL ESCROW UNLOCKED: {flag}</div>' if unlocked else ""
            body = f"""
                <h1>Dual-Custody Concurrency Vault</h1>
                <p class="subtitle">Both Key Alpha and Key Beta must be armed within an 8-second window inside this shared container.</p>
                <pre>KEY_ALPHA_STATUS: {"ARMED" if a_ok else "DISARMED"}\nKEY_BETA_STATUS:  {"ARMED" if b_ok else "DISARMED"}</pre>
                <div style="display:flex; gap:0.75rem; flex-wrap:wrap;">
                    <a class="ghost-link" href="/arm/alpha">ARM KEY ALPHA</a>
                    <a class="ghost-link" href="/arm/beta">ARM KEY BETA</a>
                </div>
                {flag_html}
            """
            return render_page("Concurrency Escrow", "escrow_vault.sh", body)

        @app.route("/arm/<which>")
        def arm(which):
            if which == "alpha":
                STATE["escrow_alpha_ts"] = time.time()
            elif which == "beta":
                STATE["escrow_beta_ts"] = time.time()
            return redirect("/")

    # =========================================================================
    # 14. AST SANDBOX: Formula evaluator context inspection
    # =========================================================================
    elif challenge_id == "ast-sandbox":
        @app.route("/", methods=["GET", "POST"])
        def index():
            res = "Enter a formula expression (e.g. 6 * 7 or CELL.value)."
            if request.method == "POST":
                expr = request.form.get("expr", "").strip()
                if expr == "CELL.value":
                    res = "Result: 42"
                elif expr == "CELL.meta":
                    res = "Result: <MetaObject keys=['owner', 'archive_key']>"
                elif expr == "CELL.meta.archive_key":
                    res = f"Result: {flag}"
                else:
                    res = f"Evaluated '{expr}' -> 0 (Try inspecting CELL, CELL.meta, etc.)"
            body = f"""
                <h1>SheetCalc Formula Engine</h1>
                <p class="subtitle">Sandboxed AST expression evaluator. Context object <code>CELL</code> is exposed in scope.</p>
                <form method="POST">
                    <input type="text" name="expr" placeholder="e.g. CELL.value" required>
                    <button type="submit">Evaluate Formula</button>
                </form>
                <pre>{res}</pre>
            """
            return render_page("SheetCalc AST", "sheet_calc.sh", body)

    # =========================================================================
    # 15. GIT ARCHAEOLOGY: Multi-page commit history viewer
    # =========================================================================
    elif challenge_id == "git-archaeology":
        commits = {
            "f9e8d7c": ("Update README deployment notes", "+ Added production startup instructions\n+ Verified environment variables"),
            "8a2d1b4": ("Refactor auth middleware", "- import legacy_auth\n+ import token_verifier"),
            "c3f9a1b": ("Revert hardcoded production secret", f"- MASTER_API_FLAG = \"{flag}\"\n+ MASTER_API_FLAG = os.getenv(\"MASTER_API_FLAG\")"),
            "a1b2c3d": ("Initial commit", "+ Created project structure\n+ Added config.py")
        }

        @app.route("/")
        def index():
            cid = request.args.get("commit", "")
            diff_view = ""
            if cid in commits:
                title, diff = commits[cid]
                diff_view = f"<hr><h3>Commit {cid}: {title}</h3><pre>{diff}</pre>"
            body = f"""
                <h1>GitWeb Repository Explorer</h1>
                <p class="subtitle">Repository: <code>nexus-core.git</code> — Browse commit log to audit historical changes.</p>
                <div style="display:flex; flex-direction:column; gap:0.5rem;">
                    <a class="ghost-link" href="/?commit=f9e8d7c">commit f9e8d7c — Update README deployment notes</a>
                    <a class="ghost-link" href="/?commit=8a2d1b4">commit 8a2d1b4 — Refactor auth middleware</a>
                    <a class="ghost-link" href="/?commit=c3f9a1b">commit c3f9a1b — Revert hardcoded production secret</a>
                    <a class="ghost-link" href="/?commit=a1b2c3d">commit a1b2c3d — Initial commit</a>
                </div>
                {diff_view}
            """
            return render_page("GitWeb Explorer", "gitweb_repo.sh", body)

    # =========================================================================
    # 16. WASM KEYCHECK: Disassembly reverse engineering
    # =========================================================================
    elif challenge_id == "wasm-keycheck":
        @app.route("/", methods=["GET", "POST"])
        def index():
            out = "Inspect the bytecode disassembly below and enter the valid 4-digit access PIN."
            if request.method == "POST":
                try:
                    pin = int(request.form.get("pin", "0"))
                    acc = (pin + 42) * 3
                    if acc == 4050:
                        out = f"VM_STACK_TOP = 4050 (MATCH!)\nVAULT FLAG: {flag}"
                    else:
                        out = f"VM_STACK_TOP = {acc} (Expected 4050 — Access Denied)"
                except ValueError:
                    out = "Invalid numeric PIN."
            body = f"""
                <h1>Bytecode PIN Verifier</h1>
                <p class="subtitle">Reverse-engineer the stack machine instructions to find the PIN.</p>
                <pre>0x00: PUSH_INPUT       ; stack = [PIN]\n0x01: PUSH_CONST 42    ; stack = [PIN, 42]\n0x02: OP_ADD           ; stack = [PIN + 42]\n0x03: PUSH_CONST 3     ; stack = [PIN + 42, 3]\n0x04: OP_MUL           ; stack = [(PIN + 42) * 3]\n0x05: PUSH_CONST 4050  ; expected = 4050\n0x06: OP_CMP_EQ</pre>
                <form method="POST">
                    <input type="number" name="pin" placeholder="Enter 4-digit PIN..." required>
                    <button type="submit">Verify PIN</button>
                </form>
                <pre>{out}</pre>
            """
            return render_page("Bytecode Verifier", "stack_vm.sh", body)

    # =========================================================================
    # 17. EVENT SOURCING: Sequence replay override
    # =========================================================================
    elif challenge_id == "event-sourcing":
        @app.route("/", methods=["GET", "POST"])
        def index():
            if request.method == "POST":
                try:
                    seq = int(request.form.get("seq", "100"))
                    role = request.form.get("role", "guest").strip()
                    STATE["event_log"].append({"seq": seq, "type": "MANUAL_EVENT", "role": role})
                    STATE["event_log"].sort(key=lambda x: x["seq"])
                except ValueError:
                    pass

            current_role = STATE["event_log"][-1]["role"]
            rows = "\n".join(f"seq={e['seq']} | type={e['type']} | role={e['role']}" for e in STATE["event_log"])
            flag_html = f'<div class="flag-banner">ELEVATED PROJECTION ACTIVE: {flag}</div>' if current_role == "admin" else ""
            body = f"""
                <h1>Event-Sourced State Projection</h1>
                <p class="subtitle">Effective Role (last event sorted by <code>seq</code>): <strong style="color:var(--amber)">{current_role}</strong> (Requires <code>admin</code>)</p>
                <pre>{rows}</pre>
                <form method="POST">
                    <input type="number" name="seq" placeholder="Event Sequence Number (e.g. 100..999)" required>
                    <input type="text" name="role" placeholder="Projected Role (e.g. guest / admin)" required>
                    <button type="submit">Append Event to Log</button>
                </form>
                {flag_html}
            """
            return render_page("Event Store", "event_projection.sh", body)

    # =========================================================================
    # 18. ZERO-KNOWLEDGE MAZE: Modular inverse puzzle
    # =========================================================================
    elif challenge_id == "zero-knowledge-maze":
        @app.route("/", methods=["GET", "POST"])
        def index():
            out = "Solve for integer x (1 <= x < 101) such that (37 * x) mod 101 == 1."
            if request.method == "POST":
                try:
                    x = int(request.form.get("x", "0"))
                    rem = (37 * x) % 101
                    if rem == 1:
                        out = f"PROOF VERIFIED: (37 * {x}) mod 101 == 1\nNEXUS MASTER FLAG: {flag}"
                    else:
                        out = f"PROOF REJECTED: (37 * {x}) mod 101 == {rem} (Expected 1)"
                except ValueError:
                    out = "Invalid integer."
            body = f"""
                <h1>Modular Ring Verifier</h1>
                <p class="subtitle">Cryptographic gatekeeper. Submit the modular multiplicative inverse $x$ of $37 \\pmod{{101}}$.</p>
                <pre>CHALLENGE EQUATION:\n(37 * x) ≡ 1 (mod 101)</pre>
                <form method="POST">
                    <input type="number" name="x" placeholder="Enter integer x..." required>
                    <button type="submit">Submit Proof</button>
                </form>
                <pre>{out}</pre>
            """
            return render_page("Modular Verifier", "zk_verifier.sh", body)

    return app


if __name__ == "__main__":
    cid = os.environ.get("CHALLENGE_ID", "chrono-vault")
    port = int(os.environ.get("PORT", "5000"))
    app = create_challenge_app(cid)
    app.run(host="0.0.0.0", port=port)
