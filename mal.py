"""mal
MyAnimeList.net wrapper functions leveraging the Jikan API.
"""

import requests
import urllib.parse

JIKAN="https://api.jikan.moe/v3"
SEARCH=JIKAN + "/search/"

# returns the top result by default
def search(cat = 'anime', name = 'naruto', limit = 1):
    return requests.get(SEARCH + f'{cat}?q={urllib.parse.quote(name)}&limit={limit}').json()