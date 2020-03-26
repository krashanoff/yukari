"""ani
AniList and AniChart wrapper functions
"""

import datetime as dt
import requests
from . import types

query = '''
query ($name: String, $category: MediaType) {
    Media (search: $name, type: $category) {
        id
        idMal
        siteUrl
        title {
            romaji
            english
            native
        }
    }
}
'''

ANILIST="https://graphql.anilist.co"
ANICHART="https://image.anichart.net"

SUPPORTED_MEDIATYPES = ['ANIME', 'MANGA']

def seasonal_chart_url(date = dt.datetime.utcnow()):
    m = date.month
    if m >= 3 and m <= 5:
        return ANICHART+"/i/Spring.jpg"
    if m >= 6 and m <= 8:
        return ANICHART+"/i/Summer.jpg"
    if m >= 9 and m <= 11:
        return ANICHART+"/i/Fall.jpg"
    if m >= 12 and m <= 2:
        return ANICHART+"/i/Winter.jpg"

async def search(cat = 'anime', name = 'naruto', limit = 1):
    cat = cat.upper()

    if cat not in SUPPORTED_MEDIATYPES:
        return None

    variables = { 'name': name, 'category': cat }
    response = requests.post(ANILIST, json={ 'query': query, 'variables': variables }).json()

    try:
        data = response['data']['Media']
        return types.Media.from_json(data)
    except:
        return None