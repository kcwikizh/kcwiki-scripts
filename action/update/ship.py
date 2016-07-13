#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from ..action import Action
import json


class UpdateShipAction(Action):
    def __init__(self):
        super(UpdateShipAction, self).__init__()

    @staticmethod
    def get():
        rep = requests.get('http://api.kcwiki.moe/ships')
        ships = rep.json()
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
        return results
