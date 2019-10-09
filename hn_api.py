"""
Hacker news api wrappers
"""

API_ROOT = 'https://hacker-news.firebaseio.com/v0/'
ITEM_TMPLT = API_ROOT + 'item/{}.json'
TOP_STORIES = API_ROOT + 'topstories.json'

def item_url(id_):
    return ITEM_TMPLT.format(id_)
