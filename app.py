# from flask import Flask, redirect, render_template, request
# import os
# import requests
# import json

# app = Flask(__name__)

# # Stored in Render Environment Variables
# CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
# CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
# REDIRECT_URI = os.getenv("REDIRECT_URI")

# STATE = "demo123"
# SCOPE = "openid profile email"


# @app.route("/")
# def index():
#     return render_template("index.html")


# @app.route("/login")
# def login():
#     # Build LinkedIn authorization URL
#     auth_url = (
#         "https://www.linkedin.com/oauth/v2/authorization"
#         f"?response_type=code"
#         f"&client_id={CLIENT_ID}"
#         f"&redirect_uri={REDIRECT_URI}"
#         f"&state={STATE}"
#         f"&scope={SCOPE}"
#     )
#     return redirect(auth_url)


# @app.route("/callback")
# def callback():
#     code = request.args.get("code")
#     state = request.args.get("state")

#     # Exchange code → access_token
#     token_url = "https://www.linkedin.com/oauth/v2/accessToken"
#     data = {
#         "grant_type": "authorization_code",
#         "code": code,
#         "redirect_uri": REDIRECT_URI,
#         "client_id": CLIENT_ID,
#         "client_secret": CLIENT_SECRET
#     }

#     token_response = requests.post(token_url, data=data)
#     token_data = token_response.json()

#     access_token = token_data.get("access_token", "No Token Returned")

#     # WhatsApp-like UI
#     return f"""
#     <html>
#     <head>
#         <title>LinkedIn OAuth</title>
#     </head>
#     <body style="margin:0; font-family:Arial; background:#f0f2f5;">

#         <div style='
#             display:flex;
#             justify-content:center;
#             align-items:center;
#             height:100vh;
#         '>

#             <div style='
#                 background:white;
#                 width:80%;
#                 max-width:1000px;
#                 height:70%;
#                 display:flex;
#                 border-radius:14px;
#                 overflow:hidden;
#                 box-shadow:0 4px 20px rgba(0,0,0,0.1);
#             '>

#                 <!-- LEFT PANEL -->
#                 <div style="
#                     flex:1;
#                     padding:40px;
#                     background:#fff;
#                 ">
#                     <h2 style='margin-top:0;'>LinkedIn OAuth Successful</h2>

#                     <p><b>Authorization Code:</b><br>{code}</p>
#                     <p><b>State:</b><br>{state}</p>

#                     <p><b>Access Token:</b><br>
#                         <div style='
#                             background:#f5f5f5;
#                             padding:10px;
#                             border-radius:6px;
#                             font-size:14px;
#                             word-wrap:break-word;
#                         '>{access_token}</div>
#                     </p>

#                     <h3 style="margin-top:40px;">Workflow:</h3>
#                     <ol style="line-height:1.8;">
#                         <li>User clicked Login with LinkedIn</li>
#                         <li>Redirected to LinkedIn OAuth page</li>
#                         <li>User approved permissions</li>
#                         <li>LinkedIn returned authorization code</li>
#                         <li>Server exchanged code for Access Token</li>
#                     </ol>
#                 </div>

#                 <!-- RIGHT PANEL -->
#                 <div style='
#                     flex:1;
#                     background:#f7f8fa;
#                     display:flex;
#                     flex-direction:column;
#                     justify-content:center;
#                     align-items:center;
#                 '>
#                     <div style='
#                         width:220px;
#                         height:220px;
#                         background:white;
#                         border-radius:12px;
#                         box-shadow:0 3px 8px rgba(0,0,0,0.15);
#                         display:flex;
#                         justify-content:center;
#                         align-items:center;
#                         font-size:18px;
#                         color:#777;
#                         margin-bottom:30px;
#                     '>
#                         AGENT QR
#                     </div>

#                     <button style='
#                         padding:14px 28px;
#                         background:#0073b1;
#                         color:white;
#                         font-size:18px;
#                         border:none;
#                         border-radius:8px;
#                         cursor:pointer;
#                         box-shadow:0 2px 6px rgba(0,0,0,0.2);
#                     '>
#                         Start Agent
#                     </button>
#                 </div>

#             </div>
#         </div>

#     </body>
#     </html>
#     """


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)





import os
import sqlite3
import uuid
import time
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from flask import Flask, redirect, render_template, request, make_response, g, Response, jsonify

# ------------------------
# Configuration / Env
# ------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET", str(uuid.uuid4()))

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")  # e.g. https://your-app.onrender.com/callback
STATE = "demo123"
SCOPE = "openid profile email w_member_social"  # add w_member_social if autopost required

# Database file (SQLite) - simple persistence for demo
DATABASE = os.path.join(os.path.dirname(__file__), "data.db")

# ------------------------
# SQLite helpers
# ------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        access_token TEXT,
        refresh_token TEXT,
        expires_at INTEGER,
        updated_at INTEGER
    );
    """)
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def save_token(session_id, access_token, refresh_token, expires_in):
    db = get_db()
    now = int(time.time())
    expires_at = now + int(expires_in) if expires_in else None
    db.execute("""
        INSERT INTO sessions(session_id, access_token, refresh_token, expires_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            expires_at=excluded.expires_at,
            updated_at=excluded.updated_at
    """, (session_id, access_token, refresh_token, expires_at, now))
    db.commit()

def get_session(session_id):
    db = get_db()
    cur = db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cur.fetchone()
    return dict(row) if row else None

# ------------------------
# Server-Sent Events helpers
# Very small pubsub in memory for demo: subscribers list of queues
# ------------------------
clients = []

def send_event(data):
    # push to all connected SSE clients (simple)
    msg = f"data: {json.dumps(data)}\n\n"
    for q in clients[:]:
        try:
            q.put(msg)
        except Exception:
            # ignore broken ones
            pass

from queue import Queue

# ------------------------
# Routes
# ------------------------
@app.before_request
def setup():
    init_db()

def ensure_session_cookie(resp, session_id=None):
    if not session_id:
        session_id = str(uuid.uuid4())
    # HttpOnly cookie so JS cannot read it (we'll also echo session id in SSE for debug)
    resp.set_cookie("session_id", session_id, httponly=True, samesite="Lax", max_age=60*60*24*30)
    return resp

@app.route("/")
def index():
    # Simple landing page with login button
    resp = make_response(render_template("index.html"))
    return ensure_session_cookie(resp)

@app.route("/login")
def login():
    # Ensure session cookie exists (we'll store tokens against this)
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": STATE,
        "scope": SCOPE
    }
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params)
    resp = redirect(auth_url)
    return ensure_session_cookie(resp, session_id)

@app.route("/callback")
def callback():
    # LinkedIn redirects here with ?code=...&state=...
    code = request.args.get("code")
    state = request.args.get("state")
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())

    # Save a workflow event
    send_event({"event": "workflow", "msg": "Got authorization code", "code": code})

    # Exchange code -> access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    token_response = requests.post(token_url, data=data)
    token_data = token_response.json()

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")  # may or may not be present
    expires_in = token_data.get("expires_in")  # seconds

    if access_token:
        save_token(session_id, access_token, refresh_token, expires_in)
        send_event({"event": "token", "msg": "Token stored", "session_id": session_id})
    else:
        send_event({"event": "error", "msg": "Token exchange failed", "details": token_data})

    # Redirect to dashboard which shows live info
    resp = redirect("/dashboard")
    return ensure_session_cookie(resp, session_id)

@app.route("/dashboard")
def dashboard():
    # Dashboard page (client JS will open SSE to receive live updates)
    resp = make_response(render_template("dashboard.html"))
    return ensure_session_cookie(resp)

@app.route("/status")
def status():
    # Return JSON of current stored session data for debugging/initial load
    session_id = request.cookies.get("session_id")
    data = {"session_id": session_id}
    if session_id:
        sess = get_session(session_id)
        if sess:
            data.update({
                "access_token": bool(sess.get("access_token")),
                "has_refresh_token": bool(sess.get("refresh_token")),
                "expires_at": sess.get("expires_at"),
                "expires_in": (sess.get("expires_at") - int(time.time())) if sess.get("expires_at") else None
            })
    return jsonify(data)

@app.route("/stream")
def stream():
    # SSE endpoint
    def gen(q: Queue):
        try:
            while True:
                msg = q.get()
                yield msg
        except GeneratorExit:
            return

    q = Queue()
    clients.append(q)
    # send initial ping
    q.put(f"data: {json.dumps({'event':'connected','msg':'connected'})}\n\n")
    return Response(gen(q), mimetype="text/event-stream")

@app.route("/autopost", methods=["POST","GET"])
def autopost():
    # Try to post a simple text update to the user's LinkedIn feed using v2 API.
    # NOTE: Requires w_member_social permission and app approved for this permission.
    session_id = request.cookies.get("session_id")
    sess = get_session(session_id) if session_id else None
    if not sess or not sess.get("access_token"):
        return jsonify({"ok": False, "error": "No access token for this session"}), 400

    access_token = sess["access_token"]

    # Fetch profile urn (to set author). We'll call the LinkedIn profile API
    profile_url = "https://api.linkedin.com/v2/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_resp = requests.get(profile_url, headers=headers)
    if profile_resp.status_code != 200:
        return jsonify({"ok": False, "error": "Failed to fetch profile", "details": profile_resp.json()}), 400

    profile = profile_resp.json()
    # The author urn format is urn:li:person:{id}
    person_id = profile.get("id")
    author = f"urn:li:person:{person_id}"

    # Build a simple UGC post (compliant format may vary; this is a best-effort)
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": "Hello from Autopost demo!"},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "CONNECTIONS"}
    }
    headers.update({"X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"})

    post_resp = requests.post(post_url, headers=headers, data=json.dumps(payload))
    if post_resp.status_code in (201, 202):
        send_event({"event": "autopost", "msg": "Autopost successful", "session": session_id})
        return jsonify({"ok": True, "message": "Posted successfully", "resp": post_resp.text})
    else:
        send_event({"event": "autopost", "msg": "Autopost failed", "details": post_resp.text})
        return jsonify({"ok": False, "error": "Post failed", "status": post_resp.status_code, "resp": post_resp.text}), 400

# ------------------------
# Utility route (clear session) - for debugging
# ------------------------
@app.route("/logout")
def logout():
    session_id = request.cookies.get("session_id")
    if session_id:
        db = get_db()
        db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        db.commit()
    resp = redirect("/")
    resp.set_cookie("session_id", "", expires=0)
    send_event({"event": "logout", "msg": "Session cleared"})
    return resp

# ------------------------
# Run
# ------------------------
if __name__ == "__main__":
    # for local testing; Render will use gunicorn
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
