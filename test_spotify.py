import os
from dotenv import load_dotenv
from modules import spotify

load_dotenv()

print("Testujem Spotify API...")
print(f"SPOTIFY_CLIENT_ID: {os.getenv('SPOTIFY_CLIENT_ID')[:10]}..." if os.getenv('SPOTIFY_CLIENT_ID') else "CHYBA")
print(f"SPOTIFY_CLIENT_SECRET: {os.getenv('SPOTIFY_CLIENT_SECRET')[:10]}..." if os.getenv('SPOTIFY_CLIENT_SECRET') else "CHYBA")

if spotify.initialize_spotify():
    print("[OK] Spotify API funguje")

    test_url = "https://open.spotify.com/track/0VHcOVctyul8gwL9bMnBdv"
    track_id = spotify.extract_spotify_id(test_url)
    print(f"Track ID: {track_id}")

    if track_id:
        track_info = spotify.get_track_info(track_id)
        print(f"Track info: {track_info}")

        if track_info:
            search_query = spotify.get_youtube_search_query(track_info)
            print(f"YouTube search query: {search_query}")
        else:
            print("[ERROR] Nepodarilo sa ziskat track info")
    else:
        print("[ERROR] Nepodarilo sa extraktovat track ID")
else:
    print("[ERROR] Spotify API nefunguje")