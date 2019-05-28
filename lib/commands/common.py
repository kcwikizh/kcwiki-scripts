import click
import json
import os

from lib.common.config import CONFIG
from lib.services.avatar import AvatarService


@click.group()
def common_cmd():
    pass


@common_cmd.command('list:ships')
def list_ships():
    if not os.path.exists('data/ship.json'):
        print('Data not exist, please update data first.')
        return
    ships = json.load(open('data/ship.json', 'r'))
    for ship in ships:
        if not ship:
            continue
        print(ship['id'], ship['name'])


@common_cmd.command('convert')
def convert():
    """Convert quotes from zh-cn to zh-tw"""
    import requests
    host = 'https://zh.kcwiki.org/api.php'
    payload = {
        'action': 'parse',
        'contentmodel': 'wikitext',
        'format': 'json',
        'uselang': 'zh-tw'
    }
    content = json.dumps(json.load(open('data/subtitles.json', 'r')), ensure_ascii=False)
    payload['text'] = content
    rep = requests.post(host, payload)
    text = rep.json()['parse']['text']['*']
    import re
    match = re.search(r'<p>(.*?)</p>', text, re.DOTALL)
    content = match.group(1).strip()
    with open('data/test.out', 'w') as fd:
        fd.write(content)
    content = re.sub(r'<.*?/>', '', content)
    content = re.sub(r'<.*?>', '', content)
    data = json.loads(content)
    print(data['1'])


@common_cmd.command('weibo:share')
def weibo_share():
    """推特头像微博分享测试命令"""
    SAVE_DIR = CONFIG['twitter']['save_dir']
    FILE_NAME = 'KanColleStaffAvatar'
    AvatarService.weibo_share(''.join([SAVE_DIR, '/', FILE_NAME, '.png']))

