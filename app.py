import os
import sqlite3
import time
import secrets
from flask import Flask, render_template, request, redirect, session, jsonify
from challenges_registry import CHALLENGES
from orchestrator import SharedDockerOrchestrator

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cyberarena_nexus_secret_2026")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyberarena.db")
orchestrator = SharedDockerOrchestrator()


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            token TEXT,
            dp TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            team_id INTEGER,
            created_at INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            invite_code TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS solves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            challenge_id TEXT NOT NULL,
            points INTEGER NOT NULL,
            first_blood INTEGER DEFAULT 0,
            solved_at INTEGER NOT NULL,
            UNIQUE(username, challenge_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS arena_feed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_text TEXT NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    default_users = [
        ("admin", "admin123", "tok_admin_123"),
        ("alice", "alice123", "tok_alice_123"),
        ("bob", "bob123", "tok_bob_123"),
    ]
    for u, p, tok in default_users:
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password, token, created_at) VALUES (?, ?, ?, ?)",
            (u, p, tok, int(time.time()))
        )
    conn.commit()
    conn.close()


def add_feed_event(text: str, ev_type: str = "info"):
    conn = get_db()
    conn.execute(
        "INSERT INTO arena_feed (event_text, event_type, created_at) VALUES (?, ?, ?)",
        (text, ev_type, time.strftime("%H:%M:%S"))
    )
    conn.commit()
    conn.close()


def get_current_username() -> str:
    if session.get("logged_in") and session.get("username"):
        return session["username"]
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        tok = auth.split(" ", 1)[1].strip()
        conn = get_db()
        row = conn.execute("SELECT username FROM users WHERE token = ?", (tok,)).fetchone()
        conn.close()
        if row:
            return row["username"]
    return ""


init_db()


# =====================================================================
#  FLASK SERVER-RENDERED ROUTES (WITH ORIGINAL CYBERARENA CRT THEME)
# =====================================================================
@app.route("/")
def home():
    if session.get("logged_in"):
        return redirect("/dashboard")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        action = request.form.get("action", "login")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            error = "Username and password are required."
        else:
            conn = get_db()
            if action == "register":
                try:
                    tok = secrets.token_hex(16)
                    conn.execute(
                        "INSERT INTO users (username, password, token, created_at) VALUES (?, ?, ?, ?)",
                        (username, password, tok, int(time.time()))
                    )
                    conn.commit()
                    session["logged_in"] = True
                    session["username"] = username
                    add_feed_event(f"New operator '{username}' joined CyberArena.", "join")
                    conn.close()
                    return redirect("/dashboard")
                except sqlite3.IntegrityError:
                    error = "Username already exists. Please sign in."
            else:
                row = conn.execute(
                    "SELECT * FROM users WHERE username = ? AND password = ?",
                    (username, password)
                ).fetchone()
                if row:
                    session["logged_in"] = True
                    session["username"] = username
                    conn.close()
                    return redirect("/dashboard")
                else:
                    error = "Invalid credentials."
            conn.close()

    return render_template("login.html", error=error)


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")

    username = session.get("username", "admin")
    conn = get_db()
    solved_rows = conn.execute(
        "SELECT challenge_id FROM solves WHERE username = ?", (username,)
    ).fetchall()
    solved_ids = {r["challenge_id"] for r in solved_rows}
    conn.close()

    challenges_view = []
    for cid, meta in CHALLENGES.items():
        status = orchestrator.get_status(cid)
        item = dict(meta)
        item["solved"] = cid in solved_ids
        item["status"] = status
        challenges_view.append(item)

    return render_template(
        "dashboard.html",
        username=username,
        challenges=challenges_view,
        engine=orchestrator.get_engine_info(),
        total_challenges=len(CHALLENGES),
        solved_count=len(solved_ids)
    )


@app.route("/start/<challenge_id>")
def start_challenge(challenge_id):
    username = get_current_username()
    if not username:
        return redirect("/login")
    if challenge_id not in CHALLENGES:
        return "Challenge not found", 404

    status = orchestrator.deploy_or_join(challenge_id, username)
    chall = CHALLENGES[challenge_id]

    if status.get("action_taken") == "DEPLOYED_NEW_SHARED_CONTAINER":
        add_feed_event(
            f"[DEPLOY] {username} deployed shared container '{chall['container_name']}' ({status['container_id']}) on :{status['port']}",
            "deploy"
        )
    else:
        add_feed_event(
            f"[SHARE] {username} joined shared container '{chall['container_name']}' ({status['operator_count']} operators sharing)",
            "share"
        )

    host = request.host.split(":")[0]
    return redirect(f"http://{host}:{status['port']}/?operator={username}")


@app.route("/api/challenge/<challenge_id>/launch", methods=["POST"])
def api_launch_challenge(challenge_id):
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    if challenge_id not in CHALLENGES:
        return jsonify({"error": "Not found"}), 404

    status = orchestrator.deploy_or_join(challenge_id, username)
    chall = CHALLENGES[challenge_id]

    if status.get("action_taken") == "DEPLOYED_NEW_SHARED_CONTAINER":
        add_feed_event(
            f"[DEPLOY] {username} deployed shared container '{chall['container_name']}' ({status['container_id']}) on :{status['port']}",
            "deploy"
        )
    else:
        add_feed_event(
            f"[SHARE] {username} joined shared container '{chall['container_name']}' ({status['operator_count']} operators sharing)",
            "share"
        )

    host = request.host.split(":")[0]
    status["url"] = f"http://{host}:{status['port']}/?operator={username}"
    return jsonify(status)


@app.route("/api/challenge/<challenge_id>/reset", methods=["POST"])
def api_reset_challenge(challenge_id):
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    if challenge_id not in CHALLENGES:
        return jsonify({"error": "Not found"}), 404

    status = orchestrator.reset_shared_container(challenge_id, username)
    chall = CHALLENGES[challenge_id]
    add_feed_event(
        f"[RESET] {username} restarted shared container '{chall['container_name']}' (ID: {status['container_id']})",
        "reset"
    )
    host = request.host.split(":")[0]
    status["url"] = f"http://{host}:{status['port']}/?operator={username}"
    return jsonify(status)


@app.route("/api/challenge/<challenge_id>/stop", methods=["POST"])
def api_stop_challenge(challenge_id):
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    if challenge_id not in CHALLENGES:
        return jsonify({"error": "Not found"}), 404

    orchestrator.stop_shared_container(challenge_id)
    chall = CHALLENGES[challenge_id]
    add_feed_event(
        f"[TERMINATE] {username} stopped shared container '{chall['container_name']}'",
        "stop"
    )
    return jsonify({"stopped": True, "status": orchestrator.get_status(challenge_id)})


@app.route("/api/submit_flag", methods=["POST"])
def submit_flag():
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    challenge_id = data.get("challenge_id", "").strip()
    submitted_flag = data.get("flag", "").strip()
    return _process_flag_submission(username, challenge_id, submitted_flag)


def _process_flag_submission(username: str, challenge_id: str, submitted_flag: str):
    chall = CHALLENGES.get(challenge_id)
    if not chall:
        return jsonify({"correct": False, "message": "Invalid challenge ID."}), 400

    if submitted_flag != chall["flag"]:
        return jsonify({"correct": False, "message": "Incorrect flag. Keep investigating the shared container!"})

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM solves WHERE username = ? AND challenge_id = ?",
        (username, challenge_id)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"correct": True, "already_solved": True, "message": "Flag already verified for your account!"})

    any_solve = conn.execute(
        "SELECT id FROM solves WHERE challenge_id = ?", (challenge_id,)
    ).fetchone()
    first_blood = 0 if any_solve else 1
    bonus = 50 if first_blood else 0
    total_pts = chall["points"] + bonus

    conn.execute(
        "INSERT INTO solves (username, challenge_id, points, first_blood, solved_at) VALUES (?, ?, ?, ?, ?)",
        (username, challenge_id, total_pts, first_blood, int(time.time()))
    )
    conn.commit()
    conn.close()

    if first_blood:
        add_feed_event(f"[FIRST BLOOD] {username} solved '{chall['title']}' (+{total_pts} PTS)!", "solve")
    else:
        add_feed_event(f"[FLAG CAPTURED] {username} solved '{chall['title']}' (+{total_pts} PTS)!", "solve")

    return jsonify({
        "correct": True,
        "first_blood": bool(first_blood),
        "points_awarded": total_pts,
        "message": f"Flag Accepted! +{total_pts} PTS" + (" (FIRST BLOOD +50 BONUS!)" if first_blood else "")
    })


@app.route("/api/state")
def api_state():
    username = get_current_username()
    if not username:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    solved_rows = conn.execute(
        "SELECT challenge_id FROM solves WHERE username = ?", (username,)
    ).fetchall()
    solved_ids = [r["challenge_id"] for r in solved_rows]

    leaderboard_rows = conn.execute("""
        SELECT username, SUM(points) as score, COUNT(id) as solves_count, SUM(first_blood) as fb_count
        FROM solves
        GROUP BY username
        ORDER BY score DESC, MAX(solved_at) ASC
        LIMIT 10
    """).fetchall()

    feed_rows = conn.execute(
        "SELECT event_text, event_type, created_at FROM arena_feed ORDER BY id DESC LIMIT 15"
    ).fetchall()
    conn.close()

    containers = {cid: orchestrator.get_status(cid) for cid in CHALLENGES}

    return jsonify({
        "engine": orchestrator.get_engine_info(),
        "solved_ids": solved_ids,
        "containers": containers,
        "leaderboard": [dict(r) for r in leaderboard_rows],
        "feed": [dict(r) for r in feed_rows]
    })


# =====================================================================
#  REACT FRONTEND API COMPATIBILITY ROUTES (/api/*)
# =====================================================================
@app.route("/api/login", methods=["POST"])
def api_react_login():
    data = request.get_json(silent=True) or {}
    u = (data.get("username") or "").strip()
    p = (data.get("password") or "").strip()
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (u, p)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Invalid username or password"}), 401
    tok = row["token"] or secrets.token_hex(16)
    conn.execute("UPDATE users SET token = ? WHERE id = ?", (tok, row["id"]))
    conn.commit()
    conn.close()
    return jsonify({
        "token": tok,
        "user": {"id": str(row["id"]), "username": row["username"], "reg_no": f"CA-{1000+row['id']}", "dp": row["dp"], "bio": row["bio"], "team_id": row["team_id"]}
    })


@app.route("/api/register", methods=["POST"])
def api_react_register():
    data = request.get_json(silent=True) or {}
    u = (data.get("username") or "").strip()
    p = (data.get("password") or "").strip()
    if len(u) < 3 or len(p) < 3:
        return jsonify({"error": "Username and password must be at least 3 characters"}), 400
    tok = secrets.token_hex(16)
    conn = get_db()
    try:
        cur = conn.execute("INSERT INTO users (username, password, token, created_at) VALUES (?, ?, ?, ?)", (u, p, tok, int(time.time())))
        uid = cur.lastrowid
        conn.commit()
        conn.close()
        return jsonify({
            "token": tok,
            "user": {"id": str(uid), "username": u, "reg_no": f"CA-{1000+uid}", "dp": "", "bio": "", "team_id": None}
        })
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Username already exists"}), 409


@app.route("/api/me")
def api_react_me():
    u = get_current_username()
    if not u:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (u,)).fetchone()
    conn.close()
    return jsonify({
        "user": {"id": str(row["id"]), "username": row["username"], "reg_no": f"CA-{1000+row['id']}", "dp": row["dp"], "bio": row["bio"], "team_id": row["team_id"]}
    })


@app.route("/api/challenges")
def api_react_challenges():
    out = []
    for cid, meta in CHALLENGES.items():
        st = orchestrator.get_status(cid)
        out.append({
            "id": cid,
            "name": meta["title"],
            "category": meta["category"],
            "difficulty": meta["difficulty"],
            "points": meta["points"],
            "description": f"{meta['description']} [Shared Docker: {meta['novel_mechanic']}]",
            "shared_status": st
        })
    return jsonify(out)


@app.route("/api/me/progress")
def api_react_progress():
    u = get_current_username()
    if not u:
        return jsonify({"solved": [], "first_bloods": [], "points": 0})
    conn = get_db()
    rows = conn.execute("SELECT challenge_id, points, first_blood FROM solves WHERE username = ?", (u,)).fetchall()
    conn.close()
    return jsonify({
        "solved": [r["challenge_id"] for r in rows],
        "first_bloods": [r["challenge_id"] for r in rows if r["first_blood"]],
        "points": sum(r["points"] for r in rows)
    })


@app.route("/api/challenges/<challenge_id>/deploy", methods=["POST"])
def api_react_deploy(challenge_id):
    u = get_current_username() or "operator"
    st = orchestrator.deploy_or_join(challenge_id, u)
    return jsonify(st)


@app.route("/api/challenges/<challenge_id>/stop", methods=["POST"])
def api_react_stop(challenge_id):
    orchestrator.stop_shared_container(challenge_id)
    return jsonify({"success": True})


@app.route("/api/challenges/<challenge_id>/heartbeat", methods=["POST"])
def api_react_heartbeat(challenge_id):
    st = orchestrator.get_status(challenge_id)
    if not st["running"]:
        return jsonify({"error": "Container not found"}), 404
    return jsonify({"success": True, "shared_operators": st["operators"]})


@app.route("/api/challenges/<challenge_id>/submit", methods=["POST"])
def api_react_submit(challenge_id):
    u = get_current_username() or "admin"
    flag = (request.get_json(silent=True) or {}).get("flag", "").strip()
    return _process_flag_submission(u, challenge_id, flag)


@app.route("/api/leaderboard")
def api_react_leaderboard():
    conn = get_db()
    rows = conn.execute("""
        SELECT u.id as user_id, u.username, u.dp, COALESCE(SUM(s.points), 0) as points, COUNT(s.id) as solves
        FROM users u LEFT JOIN solves s ON s.username = u.username
        GROUP BY u.id, u.username
        ORDER BY points DESC, u.username ASC
    """).fetchall()
    recent = conn.execute("""
        SELECT username, challenge_id as challenge, points, first_blood, solved_at
        FROM solves ORDER BY solved_at DESC LIMIT 15
    """).fetchall()
    conn.close()
    return jsonify({
        "teams": [],
        "users": [dict(r) for r in rows],
        "recent": [dict(r) for r in recent]
    })


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
