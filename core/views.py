import os
from django.shortcuts import render
from .forms import LyricsForm
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import lyricsgenius
import google.generativeai as genai

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))
genius = lyricsgenius.Genius(GENIUS_API_TOKEN, timeout=15, skip_non_songs=True, excluded_terms=["(Remix)", "(Live)"])
genai.configure(api_key=GEMINI_API_KEY)

def clean_lyrics_with_gemini(lyrics):
    prompt = (
        "Remove all non-lyrical information (such as contributor lines, translations, descriptions, or meta info) "
        "from the following lyrics and return only the clean song lyrics, well-formatted for display:\n\n"
        f"{lyrics}"
    )
    model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
    response = model.generate_content(prompt)
    return response.text.strip()

def index(request):
    lyrics = None
    error = None
    song_info = None
    track_info = None
    other_tracks = []

    if request.method == "POST":
        form = LyricsForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['song_title']
            artist = form.cleaned_data['artist_name']
            try:
                # 1. Search Track on Spotify with title & (optionally) artist
                query = f"{title} {artist}".strip()
                results = sp.search(q=query, limit=1, type='track')
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    # 2. Fetch Track/Album/Artist Details
                    artist_name = artist or track['artists'][0]['name']
                    song_title = track['name']
                    album_name = track['album']['name']
                    album_id = track['album']['id']
                    album_release_date = track['album']['release_date']
                    cover_url = track['album']['images'][0]['url'] if track['album']['images'] else ""
                    preview_url = track['preview_url']
                    spotify_url = track['external_urls']['spotify']

                    # 3. Fetch genres from artist (Spotify does not provide genre per track)
                    artist_id = track['artists'][0]['id']
                    artist_details = sp.artist(artist_id)
                    genres = artist_details.get("genres", [])

                    # 4. Get Lyrics from Genius
                    song = genius.search_song(song_title, artist_name)
                    if song:
                        lyrics = song.lyrics
                        lyrics = clean_lyrics_with_gemini(lyrics)
                    else:
                        error = "Lyrics not found on Genius."

                    # 5. Other Songs from the same Album
                    album_tracks = sp.album_tracks(album_id)
                    for item in album_tracks['items']:
                        if item['name'].lower() != song_title.lower():
                            other_tracks.append({
                                "name": item['name'],
                                "spotify_url": item['external_urls']['spotify']
                            })

                    # 6. Prepare track_info for template
                    track_info = {
                        "title": song_title,
                        "artist": artist_name,
                        "album": album_name,
                        "release_date": album_release_date,
                        "cover_url": cover_url,
                        "preview_url": preview_url,
                        "spotify_url": spotify_url,
                        "genres": genres,
                    }
                    song_info = {"title": song_title, "artist": artist_name}
                else:
                    error = "Song not found on Spotify."
            except Exception as e:
                error = str(e)
    else:
        form = LyricsForm()
    context = {
        'form': form,
        'lyrics': lyrics,
        'error': error,
        'song_info': song_info,
        'track_info': track_info,
        'other_tracks': other_tracks,
    }
    return render(request, 'core/index.html', context)