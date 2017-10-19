#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
import requests
import re
import json
import datetime
import traceback

from pyquery import PyQuery as pq
from lib.services.avatar import AvatarService
from lib.services.subtitle import SubtitleService
from ..common.utils import Echo as echo, json_pretty_dump
from ..common.utils import USER_AGENT
from ..common.config import CONFIG, DATA_DIR

UTF8 = 'utf-8'


@click.group()
def fetch_cmd():
    pass


@fetch_cmd.command(name="fetch:avatar")
def command_fetch_avatar():
    """Fetch kancolle twitter avatar"""
    AvatarService.do()


@fetch_cmd.command(name="fetch:subtitles")
@click.argument('name')
def command_fetch_subtitle(name):
    service = SubtitleService()
    if name:
        data = service.get_by_ship(name)
        json_pretty_dump(data, open('./data/test.json', 'w'))
        click.echo('Quote data saved in ./data/test.json')
    else:
        click.echo('Ship name is required.')


@fetch_cmd.command(name="fetch:twitter:info")
def command_fetch_twitter_info():
    """Fetch twitter account info"""
    try:
        click.echo('Twitter;info - fetching twitter account info...')
        raw = requests.get(CONFIG['twitter']['url']).content
        dom = pq(raw)
        with open(CONFIG['twitter']['info_path'], 'w') as fd:
            name = dom('.ProfileHeaderCard-nameLink').text()
            click.echo('Twitter:info - twitter name of official kancolle is : {}'.format(name))
            json.dump({'name': name}, fd)
    except Exception:
        click.echo('[ERROR]: Fetch twitter info failed.')
        traceback.print_exc()


@fetch_cmd.command(name="fetch:start2")
def command_fetch_start2():
    """fetch start2 json data (ooi support)"""
    fetch_start2_ooi()


def fetch_start2_ooi():
    ooi_url = CONFIG['ooi_url']
    start2_url = '{}/kcsapi/api_start2'.format(ooi_url)
    kcwiki_api_upload_url = 'http://api.kcwiki.moe/start2/upload'
    session = requests.session()
    session.headers.update({'User-Agent': USER_AGENT})
    # session.proxies = { 'http': 'http://127.0.0.1:8080'}
    echo.info('[TASK] Fetching start2 json data from OOI ...')
    # 登录 OOI
    payload = {'login_id': CONFIG['dmm_account']['username'],
               'password': CONFIG['dmm_account']['password'],
               'mode': 1}
    echo.info('[POST] {} ...'.format(ooi_url))
    rep = session.post(ooi_url, payload)
    if rep.url != '{}/kancolle'.format(ooi_url):
        echo.error('[ERROR] ooi login failed (code: {}, url: {})'.format(
            rep.status_code, rep.url))
        return
    html = rep.text
    m = re.search(r'api_token=([\d|\w]+)', html)
    if m:
        api_token = m.group(1)
    else:
        echo.error('[ERROR] api token not found')
        return
    # 获取 API_TOKEN 之后, 抓取 start2 数据
    payload = {'api_token': api_token, 'api_verno': 1}
    echo.info('[POST] {} ...'.format(start2_url))
    rep = session.post(start2_url, payload)
    raw = rep.text
    m = re.search('svdata=(.*)', raw)
    if m:
        data = json.loads(m.group(1))
        if 'api_result' in data and data['api_result'] == 1:
            start2 = data['api_data']
            today = datetime.datetime.now().strftime("%Y%m%d")
            start2_path = '{}/start2.{}.json'.format(DATA_DIR, today)
            json.dump(start2, open(start2_path, 'w'))
        else:
            echo.error('[ERROR] api result is invalid')
            print(data)
            return
    else:
        echo.error('[ERROR] start2 data not found')
        return
    # 将抓取的 start2 数据上传到 api.kcwiki.moe
    echo.info('[POST] upload start2 data to api.kcwiki.moe ...')
    password = CONFIG['api_password']
    rep = requests.post(kcwiki_api_upload_url, {'password': password,
                                                'data': json.dumps(start2)}).json()
    if 'result' not in rep or rep['result'] != 'success':
        echo.error('[ERROR] upload failed')
        if 'reason' in rep:
            echo.error('[ERROR] failure reason: {}'.format(rep['reason']))
        else:
            print(rep)
        return
    echo.info('[TASK] Done.')


def fetch_start2_dmm():
    """fetch start2 json data (auto login)"""
    session = requests.session()
    home_url = 'https://www.dmm.com'
    login_url = 'https://www.dmm.com/my/-/login/'
    get_token_url = 'https://www.dmm.com/my/-/login/ajax-get-token/'
    login_auth_url = 'https://www.dmm.com/my/-/login/auth/'
    game_url = 'http://www.dmm.com/netgame/social/-/gadgets/=/app_id=854854/'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko', 'Host': 'www.dmm.com'}
    session.headers.update(headers)
    echo.info('[INFO] visit "{}" ...'.format(login_url))
    session.get(home_url)
    rep = session.get(login_url)
    if rep.status_code != 200:
        echo.error('[ERROR] http status code: {}'.format(rep.status_code))
        return
    outer_html = rep.text
    match_dmm_token = re.search(r'''DMM_TOKEN.*?['"]([a-z0-9]{32})['"]''', outer_html)
    if match_dmm_token:
        dmm_token = match_dmm_token.group(1)
    else:
        echo.error('[ERROR] DMM_TOKEN not found')
        return
    match_token = re.search(r'''token.*?['"]([a-z0-9]{32})['"]''', outer_html)
    if match_token:
        token = match_token.group(1)
    else:
        echo.error('[ERROR] TOKEN not found')
        return
    session.headers.update({'Origin': 'https://www.dmm.com',
                    'Referer': login_url,
                    'DMM_TOKEN': dmm_token,
                    'X-Requested-With': 'XMLHttpRequest'})
    echo.info('[INFO] post "{}" ...'.format(get_token_url))
    rep = session.post(get_token_url, data={'token': token})
    if rep.status_code != 200:
        echo.error('[ERROR] http status code: {}'.format(rep.status_code))
        return
    rep_data = rep.json()
    session.headers['DMM_TOKEN'] = None
    session.headers['X-Requested-With'] = None
    username = CONFIG['dmm_account']['username']
    password = CONFIG['dmm_account']['password']
    login_payload = {
        'token': rep_data['token'],
        'login_id': username,
        'password': password,
        rep_data['login_id']: username,
        rep_data['password']: password,
        'save_login_id': 0,
        'save_password': 0
    }
    echo.info('[INFO] post "{}" ...'.format(login_auth_url))
    rep = requests.post(login_auth_url, data=login_payload, headers=headers)
    echo.info('[INFO] visit "{}" ...'.format(game_url))
    rep = session.get(game_url)
    m = re.search(r'URL\W+:\W+"(.*)",', rep.text)
    if m:
        print(m.group())
    else:
        echo.error('[ERROR] OSAPI not found')