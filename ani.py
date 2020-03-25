"""ani
AniList and AniChart wrapper functions
"""

import datetime as dt
import requests


query = '''
query ($name: String) { # Define which variables will be used in the query (id)
    Media (name: $name, type: ANIME) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
        name
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

# TODO
async def search(cat = 'anime', name = 'naruto', limit = 1):
    pass