#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import click
from os import path
from lib.common.config import DATA_DIR
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
    service = SubtitleService()
    if mode == 'main':
        subtitles = service.get(scope)
        json.dump(subtitles['zh'], open(path.join(DATA_DIR, 'subtitles.json'), 'w'))
        json.dump(subtitles['jp'], open(path.join(DATA_DIR, 'subtitlesJP.json'), 'w'))
        json.dump(subtitles['distinct'], open(path.join(DATA_DIR, 'subtitles_distinct.json'), 'w'))
    elif mode == 'deploy':
        service.deploy()
    echo.info('Done.')


