import json
import os
import re
import requests
import anthropic

from hackernews import HackerNews

SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
RANK_LIMIT = 10
CLAUDE_MODEL = "claude-sonnet-4-6"
MAX_COMMENTS = 10
MAX_ARTICLE_CHARS = 3000


def fetch_article_content(url):
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        text = re.sub(r'<[^>]+>', ' ', resp.text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:MAX_ARTICLE_CHARS]
    except Exception:
        return None


def fetch_hn_comments(hn, item_id):
    try:
        item = hn.get_item(item_id)
        kids = item.kids or []
        comments = []
        for kid_id in kids[:MAX_COMMENTS]:
            try:
                comment = hn.get_item(kid_id)
                if comment.text:
                    text = re.sub(r'<[^>]+>', ' ', comment.text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    comments.append(text)
            except Exception:
                continue
        return comments
    except Exception:
        return []


def summarize_with_claude(title, article_content, comments):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    parts = [f"記事タイトル: {title}"]

    if article_content:
        parts.append(f"\n記事本文（抜粋）:\n{article_content}")

    if comments:
        comments_text = '\n'.join(f"- {c}" for c in comments)
        parts.append(f"\nHacker Newsのコメント（抜粋）:\n{comments_text}")

    parts.append(
        "\n\n上記の内容を日本語で要約してください。"
        "記事の内容を2〜3文でまとめてください。"
        "Hacker Newsのコメントについては、くだらない意見や単なる感想・賛否表明は無視し、"
        "有用な情報や新しい視点・洞察を加えているものだけを抽出して1〜2文でまとめてください。"
        "有用なコメントがなければコメントの要約は省略してください。"
    )

    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": '\n'.join(parts)}]
    ) as stream:
        return stream.get_final_message().content[0].text


def send_message(text, target_url):
    payload_dic = {'text': text}
    requests.post(target_url, data=json.dumps(payload_dic))


def get_and_send_rankings(rank):
    hn = HackerNews()

    top_story_ids = [story.item_id for story in hn.top_stories(limit=rank)]

    for idx, id in enumerate(top_story_ids, start=1):
        item = hn.get_item(id)

        article_content = fetch_article_content(item.url)
        comments = fetch_hn_comments(hn, id)
        summary = summarize_with_claude(item.title, article_content, comments)

        # slackの表示用に <link先url|表示したいtext> のフォーマットを利用
        text = '{}. <{}|{}> [{}] view <{}|comments>\n{}'.format(
            idx,
            item.url,
            item.title,
            item.time,
            'https://news.ycombinator.com/item?id=' + str(id),
            summary
        )
        send_message(text, SLACK_WEBHOOK_URL)


if __name__ == '__main__':
    get_and_send_rankings(RANK_LIMIT)
