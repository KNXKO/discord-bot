import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import re

sp = None

def initialize_spotify():
    global sp
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

    if client_id and client_secret:
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            return True
        except Exception as e:
            print(f"Chyba pri inicializácii Spotify: {e}")
            return False
    return False

def extract_spotify_id(url):
    patterns = [
        r'spotify:track:([a-zA-Z0-9]+)',
        r'open\.spotify\.com/track/([a-zA-Z0-9]+)',
        r'spotify\.com/track/([a-zA-Z0-9]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_track_info(track_id):
    if not sp:
        return None

    try:
        track = sp.track(track_id)
        artist_names = [artist['name'] for artist in track['artists']]
        return {
            'name': track['name'],
            'artists': ', '.join(artist_names),
            'duration_ms': track['duration_ms'],
            'external_urls': track['external_urls']['spotify']
        }
    except Exception as e:
        print(f"Chyba pri získavaní informácií o skladbe: {e}")
        return None

def get_youtube_search_query(track_info):
    return f"{track_info['artists']} - {track_info['name']}"

def is_spotify_url(url):
    spotify_patterns = [
        r'spotify:track:',
        r'open\.spotify\.com/track/',
        r'spotify\.com/track/'
    ]

    for pattern in spotify_patterns:
        if re.search(pattern, url):
            return True
    return False

def is_spotify_available():
    return sp is not None