"""
crawler for site https://news.ycombinator.com. For evety entry in top 30 news 
from main page crawler will download news page and all pages from links in 
comments. 
"""
import argparse
import logging
import asyncio
import os
import re
from functools import partial

import aiohttp

import hn_api


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--log', type=str, help='path to config file',
                        default=None)
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true',
                        default=False)
    parser.add_argument('-i', '--interval', type=int, help='page fetch interval',
                        default=5)
    parser.add_argument('-n', '--num', type=int, help='number of top pages to fetch',
                        default=30)
    return parser.parse_args()


async def main(N, interval):
    async with aiohttp.ClientSession() as session:
        visited_urls = set()
        top_items_ids = await fetch_json(session, hn_api.TOP_STORIES)
        logging.debug('Top items ids: {} ...'.format(top_items_ids[:5]))
        coros = [crawl_page(session, item_id, visited_urls)
                 for item_id in top_items_ids[0:N]]
        await asyncio.gather(*coros)

async def crawl_page(session, page_id, visited_urls):
    logging.info('Started processing new page {}'.format(page_id))
    item_data = await fetch_json(session, hn_api.item_url(page_id))
    logging.debug('Fetched data for item {}'.format(page_id))
    page_url = item_data['url']
    if page_url in visited_urls:
        logging.info('Skipped, cause visited early')
        return
    logging.debug('new page data: {}'.format(item_data))
    try:
        page_html = await fetch_html(session, page_url)
    except Exception as e:
        logging.exception(e)
        return
    else:
        dir_, name = get_path(page_url)
        await save_main_page(dir_, name, page_html)
        msg = 'Page with id {} and name {} saved to disk'
        logging.debug(msg.format(page_id, name))
        visited_urls.add(page_url)
        if 'kids' in item_data:
            await crawl_comments(session, item_data['kids'])
        else:
            logging.debug('No comments for page {}'.format(page_id))
        logging.info('Finished crawling page {}'.format(page_id))


async def fetch_json(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()

async def fetch_html(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def save_main_page(dir_, fname, data):
    os.makedirs(dir_, exist_ok=True)
    with open(dir_ + '/' + fname, 'w+') as f:
        f.write(data)


def get_path(page_url):
    name = page_url.replace('/', '.')
    return './pages/' + re.sub('\.html$', '', name), name


async def crawl_comments(session, comments_ids):
    for comment_id in comments_ids:
        try:
            comment_data = fetch_json(session, hn_api.item_url(comment_id))
        except Exception as e:
            logging.exception(e)
            


if __name__ == '__main__':
    import sys
    assert sys.version_info >= (3, 7), "Python 3.7+ required"
    args = parse_args()
    logging.basicConfig(filename=args.log,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S',
                        level=logging.DEBUG if args.debug else logging.INFO)
    logging.info("ycrawler started with parameters: %s" % args)
    asyncio.run(main(args.num, args.interval))
    logging.info("Finished")