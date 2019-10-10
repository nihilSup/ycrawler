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
import urllib

import aiohttp
import aiofiles

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
        while True:
            top_items_ids = await fetch_json(session, hn_api.TOP_STORIES)
            logging.debug('Top items ids: {} ...'.format(top_items_ids[:5]))
            main_fut = asyncio.gather(
                *[crawl_page(session, item_id, visited_urls)
                  for item_id in top_items_ids[0:N]])
            main_fut.add_done_callback(lambda fut: logging.info('Finished fetching top news'))
            await asyncio.sleep(interval)
        

async def crawl_page(session, page_id, visited_urls):
    logging.info('Started processing new page {}'.format(page_id))
    item_data = await fetch_json(session, hn_api.item_url(page_id))
    logging.debug('Fetched data for item {}'.format(page_id))
    page_url = item_data['url']
    if page_url in visited_urls:
        logging.info('Skipped, cause visited early')
        return
    logging.debug('new page data: {}'.format(item_data))
    dir_ = './pages/' + re.sub('\.html$', '', page_url.replace('/', '.'))
    asyncio.create_task(download_page(session, page_url, dir_, visited_urls))
    if 'kids' in item_data:
        logging.info('Start crawling comments for page {}'.format(page_id))
        await asyncio.gather(*[crawl_comments(session, comm_id, dir_)
                                for comm_id in item_data['kids']])
        logging.info('Finished crawling comments for page {}'.format(page_id))
    else:
        logging.info('No comments for page {}'.format(page_id))
    logging.info('Finished crawling page {}'.format(page_id))


async def fetch_json(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()

async def fetch_html(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def save_page(data, fname, dir_):
    os.makedirs(dir_, exist_ok=True)
    async with aiofiles.open(dir_ + '/' + fname, 'w+') as f:
        await f.write(data)


async def download_page(session, page_url, dir_, vstd_urls):
    logging.info('Downloading new page')
    if page_url in vstd_urls:
        logging.info('Skipped previously visited page')
        return
    try:
        page_html = await fetch_html(session, page_url)
        name = page_url.replace('/', '.')
        if page_url not in vstd_urls:
            await save_page(page_html, name, dir_)
            vstd_urls.add(page_url)
            msg = 'Page <{}> saved to disk'
            logging.info(msg.format(page_url))
        else:
            logging.info('Skipped previously visited page')
    except Exception as e:
        msg = 'Exception while downloading page <{}>'
        logging.exception(msg.format(page_url))
        logging.exception(e)
        return


async def crawl_comments(session, comment_id, dir_, pattern=None, vstd_urls=None):
    if not pattern:
        pattern = re.compile(r'href="(.*?)"')
    if not vstd_urls:
        vstd_urls = set()
    try:
        comment_data = await fetch_json(session, hn_api.item_url(comment_id))
    except Exception as e:
        logging.exception(e)
        return
    else:
        logging.debug('Comment {} data:\n{}'.format(comment_id, comment_data))
        comm_text = comment_data.get('text', '')
        logging.debug('Comment {} text:\n{}'.format(comment_id, comm_text))
        for link in pattern.findall(comm_text):
            link = link.replace('&#x2F;', '/')
            if link not in vstd_urls:
                asyncio.create_task(download_page(session, link, dir_,
                                                  vstd_urls))
        kids_ids = comment_data.get('kids', [])
        if kids_ids:
            logging.info('crawling comments for comment {}'.format(comment_id))
            await asyncio.gather(*[crawl_comments(session, kid_id, dir_,
                                                vstd_urls=vstd_urls)
                                for kid_id in kids_ids])


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