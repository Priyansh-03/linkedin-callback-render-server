from flask import Flask, redirect, render_template, request
import os
import requests
import json

app = Flask(__name__)

# Stored in Render Environment Variables
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

STATE = "demo123"
SCOPE = "openid profile email"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    # Build LinkedIn authorization URL
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={STATE}"
        f"&scope={SCOPE}"
    )
    return redirect(auth_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state")

    # Exchange code → access_token
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

    access_token = token_data.get("access_token", "No Token Returned")

    # WhatsApp-like UI
    return f"""
    <html>
    <head>
        <title>LinkedIn OAuth</title>
    </head>
    <body style="margin:0; font-family:Arial; background:#f0f2f5;">

        <div style='
            display:flex;
            justify-content:center;
            align-items:center;
            height:100vh;
        '>

            <div style='
                background:white;
                width:80%;
                max-width:1000px;
                height:70%;
                display:flex;
                border-radius:14px;
                overflow:hidden;
                box-shadow:0 4px 20px rgba(0,0,0,0.1);
            '>

                <!-- LEFT PANEL -->
                <div style="
                    flex:1;
                    padding:40px;
                    background:#fff;
                ">
                    <h2 style='margin-top:0;'>LinkedIn OAuth Successful</h2>

                    <p><b>Authorization Code:</b><br>{code}</p>
                    <p><b>State:</b><br>{state}</p>

                    <p><b>Access Token:</b><br>
                        <div style='
                            background:#f5f5f5;
                            padding:10px;
                            border-radius:6px;
                            font-size:14px;
                            word-wrap:break-word;
                        '>{access_token}</div>
                    </p>

                    <h3 style="margin-top:40px;">Workflow:</h3>
                    <ol style="line-height:1.8;">
                        <li>User clicked Login with LinkedIn</li>
                        <li>Redirected to LinkedIn OAuth page</li>
                        <li>User approved permissions</li>
                        <li>LinkedIn returned authorization code</li>
                        <li>Server exchanged code for Access Token</li>
                    </ol>
                </div>

                <!-- RIGHT PANEL -->
                <div style='
                    flex:1;
                    background:#f7f8fa;
                    display:flex;
                    flex-direction:column;
                    justify-content:center;
                    align-items:center;
                '>
                    <div style='
                        width:220px;
                        height:220px;
                        background:white;
                        border-radius:12px;
                        box-shadow:0 3px 8px rgba(0,0,0,0.15);
                        display:flex;
                        justify-content:center;
                        align-items:center;
                        font-size:18px;
                        color:#777;
                        margin-bottom:30px;
                    '>
                        AGENT QR
                    </div>

                    <button style='
                        padding:14px 28px;
                        background:#0073b1;
                        color:white;
                        font-size:18px;
                        border:none;
                        border-radius:8px;
                        cursor:pointer;
                        box-shadow:0 2px 6px rgba(0,0,0,0.2);
                    '>
                        Start Agent
                    </button>
                </div>

            </div>
        </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
