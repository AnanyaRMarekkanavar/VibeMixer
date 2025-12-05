from flask import Flask, request, redirect, session, render_template_string
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this to anything random and private

# ------------------- SPOTIFY CONFIG -------------------
SPOTIFY_CLIENT_ID = "b0108671c22f41d49d28f9d892b2ba35"
SPOTIFY_CLIENT_SECRET = "f61a5d8ca25b45138f32b119755bd8d7"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:5000/callback"
SCOPE = "playlist-modify-public playlist-modify-private user-read-private"

# ------------------- FRONTEND (SURVEY PAGE) -------------------
SURVEY_HTML = """
<html>
<head>
    <title>🎵 Mood Playlist Generator</title>
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #191414, #1DB954);
            color: white;
            text-align: center;
            padding: 50px;
        }
        form {
            background: rgba(0,0,0,0.6);
            display: inline-block;
            padding: 40px;
            border-radius: 20px;
        }
        label {
            display: block;
            margin-top: 20px;
            font-size: 1.2em;
        }
        select, input[type="text"], input[type="number"] {
            padding: 10px;
            border-radius: 10px;
            border: none;
            margin-top: 10px;
            width: 80%;
            text-align: center;
        }
        input[type="submit"] {
            margin-top: 30px;
            padding: 15px 30px;
            background: #1DB954;
            border: none;
            border-radius: 30px;
            color: white;
            font-size: 1.1em;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background: #17a24e;
        }
    </style>
</head>
<body>
    <h1>🎧 Create Your Custom Spotify Playlist</h1>
    <form action="/login" method="post">
        <label>Mood</label>
        <select name="mood" required>
            <option value="happy">Happy</option>
            <option value="sad">Sad</option>
            <option value="romantic">Romantic</option>
            <option value="chill">Chill</option>
            <option value="party">Party</option>
            <option value="focus">Focus</option>
        </select>

        <label>Favorite Artist</label>
        <input type="text" name="artist" placeholder="e.g. Arijit Singh or Taylor Swift">

        <label>Want trending songs on top?</label>
        <select name="trending" required>
            <option value="yes">Yes</option>
            <option value="no">No</option>
        </select>

        <label>How many songs?</label>
        <input type="number" name="length" min="5" max="30" value="10">

        <input type="submit" value="🎶 Generate Playlist">
    </form>
</body>
</html>
"""

# ------------------- ROUTES -------------------

@app.route("/", methods=["GET"])
def home():
    return SURVEY_HTML


@app.route("/login", methods=["POST"])
def login():
    session['mood'] = request.form['mood']
    session['artist'] = request.form['artist']
    session['trending'] = request.form['trending']
    session['length'] = int(request.form['length'])

    sp_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    )

    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    )

    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)  # ✅ Fix for latest spotipy

    access_token = token_info.get('access_token')
    if not access_token:
        return "Error: No access token received from Spotify. Try again."

    sp = spotipy.Spotify(auth=access_token)
    user_id = sp.current_user()['id']

    playlist_url, playlist_tracks = create_custom_playlist(
        sp,
        user_id,
        session['mood'],
        session['artist'],
        session['trending'],
        session['length']
    )

    # Render playlist info
    track_list_html = "<ul style='list-style:none; padding:0;'>"
    for name, artist in playlist_tracks:
        track_list_html += f"<li>🎵 <b>{name}</b> — {artist}</li>"
    track_list_html += "</ul>"

    return render_template_string(f"""
    <html>
    <head>
        <title>Your Playlist 🎵</title>
        <style>
            body {{
                background: linear-gradient(135deg, #191414, #1DB954);
                color: white;
                font-family: 'Poppins', sans-serif;
                text-align: center;
                padding: 50px;
            }}
            a {{
                background: #1DB954;
                color: white;
                padding: 12px 25px;
                border-radius: 25px;
                text-decoration: none;
            }}
            a:hover {{
                background: #17a24e;
            }}
        </style>
    </head>
    <body>
        <h1>✅ Your playlist is ready!</h1>
        <p>Here’s your personalized Spotify playlist:</p>
        <a href="{playlist_url}" target="_blank">🎧 Open in Spotify</a>
        <h2 style="margin-top:40px;">Track List</h2>
        {track_list_html}
        <br><br>
        <a href="/">← Create another</a>
    </body>
    </html>
    """)

# ------------------- PLAYLIST CREATION LOGIC -------------------

def create_custom_playlist(sp, user_id, mood, artist, trending, playlist_length):
    playlist_name = f"{mood.capitalize()} Vibes by {artist}" if artist else f"{mood.capitalize()} Vibes"
    playlist_desc = f"Generated by VibeMixer 🎶 | Mood: {mood}, Artist: {artist or 'Various'}"

    playlist = sp.user_playlist_create(user_id, playlist_name, public=True, description=playlist_desc)

    search_queries = []
    if artist:
        search_queries.append(f"{mood} {artist}")
        search_queries.append(artist)
    else:
        search_queries.append(mood)

    if trending == "yes":
        search_queries.append(f"top {mood} songs")
        search_queries.append("top hits")
        search_queries.append("trending songs")

    track_uris = []
    playlist_tracks = []

    for query in search_queries:
        results = sp.search(q=query, type="track", limit=20)
        for item in results['tracks']['items']:
            uri = item['uri']
            if uri not in track_uris:
                track_uris.append(uri)
                playlist_tracks.append((item['name'], item['artists'][0]['name']))
            if len(track_uris) >= playlist_length:
                break
        if len(track_uris) >= playlist_length:
            break

    if len(track_uris) < playlist_length:
        results = sp.search(q="popular songs", type="track", limit=50)
        for item in results['tracks']['items']:
            uri = item['uri']
            if uri not in track_uris:
                track_uris.append(uri)
                playlist_tracks.append((item['name'], item['artists'][0]['name']))
            if len(track_uris) >= playlist_length:
                break

    track_uris = track_uris[:playlist_length]
    playlist_tracks = playlist_tracks[:playlist_length]

    sp.playlist_add_items(playlist['id'], track_uris)
    return playlist['external_urls']['spotify'], playlist_tracks


# ------------------- RUN APP -------------------
if __name__ == "__main__":
    app.run(debug=True)
