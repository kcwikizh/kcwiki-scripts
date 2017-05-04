import click
import json
import os


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
