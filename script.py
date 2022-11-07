import datetime
import json
import os
import requests

from hackernews import HackerNews

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
RANK_LIMIT = 10

def send_message(text, target_url):
    payload_dic = { 'text': text }
    requests.post(target_url, data=json.dumps(payload_dic))

def get_and_send_rankings(rank):
    hn = HackerNews()

    top_story_ids = [story.item_id for story in hn.top_stories(limit=rank)]

    idx = 1
    for id in top_story_ids:
        item = hn.get_item(id)
        # slackの表示用に <link先url|表示したいtext> のフォーマットを利用
        text = '{}. <{}|{}> [{}] view <{}|comments>'.format(idx, item.url, item.title, item.time, 'https://news.ycombinator.com/item?id=' + str(id))
        send_message(text, SLACK_WEBHOOK_URL)
        idx += 1

if __name__ == '__main__':
    get_and_send_rankings(RANK_LIMIT)
