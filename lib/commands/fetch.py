#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
import requests
import re
from ..common.utils import Echo as echo
from ..common.config import config

UTF8 = 'utf-8'


@click.group()
def fetch_cmd():
    pass


@fetch_cmd.command(name="fetch:start2")
def fetch_start2():
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
    username = config['dmm_account']['username']
    password = config['dmm_account']['password']
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