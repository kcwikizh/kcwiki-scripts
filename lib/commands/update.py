#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import click
from ..services.api import KcwikiApi as Api


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
        except IndexError as e:
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
    ships = Api.ships()
