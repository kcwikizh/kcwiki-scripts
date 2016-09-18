#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import click
import datetime
import requests
from os import path
from shutil import copyfile
from lib.common.config import data_dir, config
from lib.common.utils import Echo as echo
from lib.services.api import KcwikiApi as Api
from lib.services.subtitle import SubtitleService


@click.group()

def update_cmd():
    pass


@update_cmd.command(name='update:ships')
def update_ships():
    """Update ships data from api.kcwiki.moe"""
    ships = Api.ships()
    results = []
    max_id = 0
    for ship in ships:
        max_id = int(ship['id']) if int(ship['id']) > max_id else max_id
    for i in range(max_id+1):
        results.append({})
    for ship in ships:
        _id = int(ship['id'])
        try:
            results[_id] = ship
        except IndexError:
            print(_id)
            print(ship)
    with open('data/ship.json', 'w') as f:
        json.dump(results, f)
    if len(results) > 0:
        click.echo('update ship data success!')
    else:
        click.echo('no data')


@update_cmd.command(name='update:enemies')
def update_enemies():
    """Update enemies data from api.kcwiki.moe"""
    pass


@update_cmd.command(name='update:subtitles')
@click.argument('mode', default='main')
@click.option('--scope', '-s', default='all')
@click.pass_obj
def update_subtitles(ctx, mode, scope):
    """Update kancolle musume quotes"""
    if mode in ['main', 'deploy']:
        subtitles_service = SubtitleService()
        subtitles = subtitles_service.get(scope)
        json.dump(subtitles['zh'], open(path.join(data_dir, 'subtitles.json'), 'w'))
        json.dump(subtitles['jp'], open(path.join(data_dir, 'subtitlesJP.json'), 'w'))
        json.dump(subtitles['distinct'], open(path.join(data_dir, 'subtitles_distinct.json'), 'w'))
        if mode == 'deploy':
            env = config['env']
            now = datetime.datetime.now().strftime('%Y%m%d%H')
            deploy_filename = now + '.json'
            deploy_dir = config[env]['subtitle']
            copyfile(path.join(data_dir, 'subtitles.json'), path.join(deploy_dir, 'zh-cn', deploy_filename))
            copyfile(path.join(data_dir, 'subtitlesJP.json'), path.join(deploy_dir, 'jp', deploy_filename))
            copyfile(path.join(data_dir, 'subtitles_distinct.json'), path.join(deploy_dir, 'subtitles_distinct.json'))
            meta_file = path.join(deploy_dir, 'meta.json')
            meta = json.load(open(meta_file, 'r'))
            meta['latest'] = deploy_filename[:-5]
            json.dump(meta, open(meta_file, 'w'))
            # Purge cache in api.kcwiki.moe
            requests.get('http://api.kcwiki.moe/purge/subtitles')
    echo.info('Done.')


