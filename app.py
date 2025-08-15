import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import requests
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials
import sqlite3
import json
import urllib.parse

# Load environment variables
load_dotenv()

if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
    })
    try:
        firebase_admin.initialize_app(cred)
    except Exception:
        pass

external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
]
app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}]
)
app.title = "YouTube Focus - Distraction Free"
server = app.server

def init_db():
    conn = sqlite3.connect('user_preferences.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id TEXT PRIMARY KEY,
                  dark_mode INTEGER,
                  search_history TEXT,
                  created_at TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# ---------- UI COMPONENTS ----------
def navbar():
    return dbc.Navbar(
        dbc.Container(
            [
                html.A(
                    dbc.Row(
                        [
                            dbc.Col(html.Img(src="/assets/logo2.png",
                                             style={
                                                "width": "34px",
                                                "height": "34px",
                                                "borderRadius": "50%",
                                                "objectFit": "cover",
                                                "display": "block",
                                                "border": "1px solid rgba(255,255,255,0.15)"
                                            })),
                            dbc.Col(dbc.NavbarBrand("YouTube Focus", className="ms-2 fw-bold")),
                        ],
                        align="center",
                        className="g-0"
                    ),
                    href="/",
                    className="navbar-brand"
                ),
                dbc.Button(
                    [html.I(className="fas fa-house me-2"), "Home"],
                    id="home-button",
                    color="light",
                    outline=True,
                    className="ms-3"
                ),
                html.Div(id="nav-space", className="ms-auto"),
                html.Div(id="user-auth-section", className="ms-3")
            ],
            fluid=True,
            className="px-3"
        ),
        color="dark",
        dark=True,
        sticky="top",
        className="navbar-main shadow-sm"
    )

def hero_section():
    return html.Section(
        dbc.Container(
            [
                dbc.Row(
                    dbc.Col(
                        [
                            html.Span("DISTRACTION-FREE YOUTUBE", className="section-badge"),
                            html.H1("Focus on What Matters", className="hero-title"),
                            html.P("Search videos without the noise — no feeds, no shorts, no clutter.", className="hero-subtitle"),
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id="search-input-hero",
                                        placeholder="Search videos...",
                                        type="text",
                                        className="search-input",
                                        debounce=False,
                                    ),
                                    dbc.Button(
                                        [html.I(className="fas fa-search me-2"), "Search"],
                                        id="search-button-hero",
                                        color="danger",
                                        className="search-button"
                                    ),
                                    dbc.Button(
                                        html.I(className="fas fa-microphone"),
                                        id="voice-search-btn-hero",
                                        color="light",
                                        className="voice-button"
                                    ),
                                ],
                                className="search-group mt-3"
                            ),
                            html.Small("Press Enter to search", className="search-hint mt-2 d-block")
                        ],
                        md=10,
                        lg=8,
                        className="mx-auto text-center py-5"
                    )
                )
            ],
            fluid=True,
            className="hero-container"
        ),
        className="hero-section"
    )

def main_content():
    return html.Main(
        dbc.Container(
            [
                html.Div(id="search-results-header", className="results-header"),
                dbc.Row(id="page-content", className="results-grid")
            ],
            fluid=True,
            className="py-4"
        ),
        className="main-content"
    )

def footer():
    return html.Footer(
        dbc.Container(
            [
                dbc.Row(
                    dbc.Col(
                        html.Div([
                            html.Span("YouTube Focus", className="footer-brand fw-bold"),
                            html.Span(" • "),
                            html.Small("© 2025 All rights reserved", className="footer-copyright"),
                        ]),
                        width=12
                    )
                )
            ],
            fluid=True,
            className="py-3 text-center"
        ),
        className="app-footer"
    )

# App layout
app.layout = html.Div(
    [
        dcc.Store(id='user-store', storage_type='session'),
        dcc.Location(id='url', refresh=False),

        html.Div(id="voice-search-output", style={"display": "none"}),
        html.Div(id="firebase-user", style={"display": "none"}),

        navbar(),
        hero_section(),
        main_content(),
        footer(),

        html.Script(src="https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js"),
        html.Script(src="https://www.gstatic.com/firebasejs/8.10.0/firebase-auth.js"),
        html.Script(
            f"""
            // CLIENT-SIDE FIREBASE CONFIG & AUTH HANDLERS
            const firebaseConfig = {{
                apiKey: "{os.getenv('FIREBASE_API_KEY') or ''}",
                authDomain: "{os.getenv('FIREBASE_AUTH_DOMAIN') or ''}",
                projectId: "{os.getenv('FIREBASE_PROJECT_ID') or ''}",
                storageBucket: "{os.getenv('FIREBASE_STORAGE_BUCKET') or ''}",
                messagingSenderId: "{os.getenv('FIREBASE_MESSAGING_SENDER_ID') or ''}",
                appId: "{os.getenv('FIREBASE_APP_ID') or ''}"
            }};
            try {{
                if (!window.firebase?.apps?.length) {{
                    firebase.initializeApp(firebaseConfig);
                }}
            }} catch (e) {{
                console.warn("Firebase init failed:", e);
            }}

            function signInWithGoogle() {{
                const provider = new firebase.auth.GoogleAuthProvider();
                firebase.auth().signInWithPopup(provider)
                    .then((result) => {{
                        const user = result.user;
                        user.getIdToken().then((token) => {{
                            const payload = {{
                                email: user.email,
                                displayName: user.displayName,
                                token: token
                            }};
                            const el = document.getElementById('firebase-user');
                            if (el) el.innerText = JSON.stringify(payload);
                        }});
                    }}).catch((err) => {{
                        console.error("Sign-in error:", err);
                        alert("Google Sign-in failed. Check console.");
                    }});
            }}

            function signOutGoogle() {{
                firebase.auth().signOut()
                    .then(() => {{
                        const el = document.getElementById('firebase-user');
                        if (el) el.innerText = "";
                    }})
                    .catch((err) => {{
                        console.error("Sign-out failed:", err);
                    }});
            }}

            // wire auth buttons (they are rendered by Dash; use MutationObserver)
            (function wireAuthButtons() {{
                function wire() {{
                    const inBtn = document.getElementById('signin-button');
                    if (inBtn && !inBtn.dataset._wired) {{
                        inBtn.addEventListener('click', (e) => {{ e.preventDefault(); signInWithGoogle(); }});
                        inBtn.dataset._wired = '1';
                    }}
                    const outBtn = document.getElementById('signout-button');
                    if (outBtn && !outBtn.dataset._wired) {{
                        outBtn.addEventListener('click', (e) => {{ e.preventDefault(); signOutGoogle(); }});
                        outBtn.dataset._wired = '1';
                    }}
                }}
                const obs = new MutationObserver(wire);
                obs.observe(document.body, {{ childList: true, subtree: true }});
                document.addEventListener('DOMContentLoaded', wire);
            }})();

            // VOICE SEARCH: Web Speech API
            (function wireVoice() {{
                const micBtnId = 'voice-search-btn-hero';
                function startRecognition() {{
                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                    if (!SpeechRecognition) {{
                        alert('Speech Recognition API not supported in this browser.');
                        return;
                    }}
                    const rec = new SpeechRecognition();
                    rec.lang = 'en-US';
                    rec.interimResults = false;
                    rec.maxAlternatives = 1;
                    rec.onresult = (ev) => {{
                        const text = ev.results[0][0].transcript || '';
                        const voiceEl = document.getElementById('voice-search-output');
                        if (voiceEl) {{
                            voiceEl.innerText = text;
                        }}
                        const input = document.getElementById('search-input-hero');
                        const searchBtn = document.getElementById('search-button-hero');
                        if (input) input.value = text;
                        if (searchBtn) searchBtn.click();
                    }};
                    rec.onerror = (e) => {{
                        console.error('Speech recognition error', e);
                        alert('Voice recognition failed. See console for details.');
                    }};
                    rec.start();
                }}

                function wire() {{
                    const btn = document.getElementById(micBtnId);
                    if (btn && !btn.dataset._wired) {{
                        btn.addEventListener('click', (e) => {{
                            e.preventDefault();
                            startRecognition();
                        }});
                        btn.dataset._wired = '1';
                    }}
                }}
                const obs = new MutationObserver(wire);
                obs.observe(document.body, {{ childList: true, subtree: true }});
                document.addEventListener('DOMContentLoaded', wire);
            }})();
            """
        )
    ],
    className="app-wrapper"
)

@app.callback(
    Output("user-auth-section", "children"),
    Input("firebase-user", "children"),
    prevent_initial_call=False
)
def update_auth_section(firebase_user_json):
    try:
        payload = json.loads(firebase_user_json) if firebase_user_json else None
    except Exception:
        payload = None

    if payload and isinstance(payload, dict) and payload.get("email"):
        user_badge = dbc.Badge(payload.get("email"), color="light", text_color="dark", className="me-2")
        signout = dbc.Button([html.I(className="fas fa-sign-out-alt me-2"), "Sign out"],
                             id="signout-button", color="light", outline=True, size="sm")
        return html.Div([user_badge, signout], className="d-flex align-items-center")
    else:
        signin = dbc.Button([html.I(className="fab fa-google me-2"), "Sign in with Google"],
                            id="signin-button", color="light", outline=True, size="sm")
        return signin

@app.callback(
    [Output("page-content", "children"),
     Output("search-results-header", "children"),
     Output("search-input-hero", "value")],  # CLEAR input when Home is clicked
    [Input("search-button-hero", "n_clicks"),
     Input("search-input-hero", "n_submit"),
     Input("voice-search-output", "children"),
     Input("home-button", "n_clicks")],
    [State("search-input-hero", "value")],
    prevent_initial_call=False
)
def handle_search(search_click, enter_submit, voice_text, home_click, search_value):
    ctx = callback_context
    triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None

    if triggered and triggered.startswith("home-button"):
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            msg = dbc.Col(html.Div("YouTube API key is not configured", className="empty-state"), xs=12)
            return [msg], "", ""   # third output clears input

        region = os.getenv("YOUTUBE_REGION_CODE", "IN")
        url = ("https://www.googleapis.com/youtube/v3/videos"
               f"?part=snippet&chart=mostPopular&maxResults=20&regionCode={region}&key={api_key}")
        try:
            resp = requests.get(url, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            if not items:
                msg = dbc.Col(html.Div("No trending videos found.", className="empty-state"), xs=12)
                return [msg], html.H5("Trending"), ""
            cols = []
            for item in items:
                vid = item.get("id")
                snip = item.get("snippet", {})
                thumb = (snip.get("thumbnails", {}) or {}).get("medium", {}).get("url", "")
                title = snip.get("title", "Untitled")
                desc = snip.get("description", "")
                channel = snip.get("channelTitle", "Unknown")
                card = dbc.Card(
                    [
                        dbc.CardImg(src=thumb, top=True, className="video-thumbnail"),
                        dbc.CardBody([
                            dbc.Badge("Trending", color="danger", className="me-2"),
                            html.H5(title, className="video-title"),
                            html.Small(channel, className="d-block text-muted mb-2"),
                            html.P(desc, className="video-description", style={"maxHeight": "4.5rem", "overflow": "hidden"})
                        ]),
                        dbc.CardFooter(
                            dbc.Button("Watch", color="danger", href=f"https://www.youtube.com/watch?v={vid}", target="_blank", className="w-100")
                        )
                    ], className="video-card h-100 rounded-4 shadow-sm"
                )
                cols.append(dbc.Col(card, xs=12, sm=6, lg=4, xl=3, className="mb-4"))
            header = html.H5([html.I(className="fa-solid fa-fire me-2"), "Trending Videos"])
            return cols, header, ""   # clear search input
        except Exception as e:
            msg = dbc.Col(html.Div(f"Error fetching trending videos: {e}", className="empty-state"), xs=12)
            return [msg], "", ""

    query = ""
    if voice_text and str(voice_text).strip():
        query = str(voice_text).strip()
    elif search_value and str(search_value).strip():
        query = str(search_value).strip()
    else:
        placeholder = dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    dbc.Badge("Welcome", color="danger", className="me-2"),
                    html.H4("Search YouTube without the noise", className="fw-bold mb-2"),
                    html.P("Use the search bar above to find videos. Results will appear in a clean grid.", className="text-muted mb-0")
                ]),
                className="welcome-card rounded-4 shadow-sm py-4 px-3"
            ),
            xs=12
        )
        return [placeholder], "", search_value or ""

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        msg = dbc.Col(html.Div("YouTube API key is not configured", className="empty-state"), xs=12)
        return [msg], "", search_value or ""

    url = (
        "https://www.googleapis.com/youtube/v3/search"
        f"?part=snippet&q={urllib.parse.quote(query)}&type=video&maxResults=20&key={api_key}"
    )

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        if not items:
            msg = dbc.Col(html.Div("No results found for your search", className="empty-state"), xs=12)
            header = html.H5([html.I(className="fa-solid fa-list me-2"), "Results for:", html.Span(f" {query}", className="text-muted")])
            return [msg], header, query

        cols = []
        for it in items:
            vid = it.get("id", {}).get("videoId", "")
            snip = it.get("snippet", {})
            thumb = (snip.get("thumbnails", {}) or {}).get("medium", {}).get("url", "")
            title = snip.get("title", "Untitled")
            desc = snip.get("description", "")
            channel = snip.get("channelTitle", "Unknown")
            card = dbc.Card(
                [
                    dbc.CardImg(src=thumb, top=True, className="video-thumbnail"),
                    dbc.CardBody([
                        dbc.Badge("Video", color="danger", className="me-2"),
                        html.H5(title, className="video-title"),
                        html.Small(channel, className="d-block text-muted mb-2"),
                        html.P(desc, className="video-description", style={"maxHeight": "4.5rem", "overflow": "hidden"})
                    ]),
                    dbc.CardFooter(
                        dbc.Button("Watch Video", color="danger", href=f"https://www.youtube.com/watch?v={vid}", target="_blank", className="w-100")
                    )
                ],
                className="video-card h-100 rounded-4 shadow-sm"
            )
            cols.append(dbc.Col(card, xs=12, sm=6, lg=4, xl=3, className="mb-4"))

        header = html.H5([html.I(className="fa-solid fa-list me-2"), "Results for:", html.Span(f" {query}", className="text-muted"), html.Span(f" • {len(cols)} videos", className="text-muted ms-2")])
        return cols, header, query

    except requests.exceptions.RequestException as e:
        msg = dbc.Col(html.Div(f"Error connecting to YouTube API: {e}", className="empty-state"), xs=12)
        return [msg], "", search_value or ""
    except Exception as e:
        msg = dbc.Col(html.Div(f"An unexpected error occurred: {e}", className="empty-state"), xs=12)
        return [msg], "", search_value or ""

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
