# Recursive Async crawler for news.ycombinator.com

## About

crawls top N news from site:

- Downloads page from news
- Traverse comments and downloads all links in them
- Results are been cached, i.e. crawler doesn't visit same pages
- Redo every 'interval' seconds

## How to use

### Install requirements

'''shell
pip install -r requirements.txt
'''

### Run

'''shell
python ycrawler.py -n 30 -i 60
'''

There are several arguments:

- -n tells number of top news to download
- -i interval of fetching of n top news in seconds
- -d debug logging
- -l where to store log file
