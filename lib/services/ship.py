import json
from os import path
from .api import KcwikiApi
from ..common.config import data_dir
from ..common.utils import has_keys, Echo as echo


class ShipService(object):
    def __init__(self):
        ship_path = path.join(data_dir, 'ship.json')
        if path.exists(ship_path):
            self.ships = json.load(open(ship_path, 'r'))
        else:
            echo.info('"ship.json" is not exist, fetch ship data now..')
            self.ships = ShipService.update()
        self.ships = self.ships[:490]
        self.name_map = {}
        self.wiki_id_map = {}
        for ship in self.ships:
            if has_keys(ship, 'name'):
                self.name_map[ship['name']] = ship
            if has_keys(ship, 'chinese_name'):
                self.name_map[ship['chinese_name']] = ship
            if has_keys(ship, 'wiki_id'):
                self.wiki_id_map[ship['wiki_id']] = ship

    def get_kai_set(self):
        """获取已改船的集合"""
        ships = self.ships
        kaiship = set()
        for ship in ships:
            if has_keys(ship, 'after_ship_id'):
                kaiship.add(int(ship['after_ship_id']))
        return kaiship

    def get(self, name=None, wiki_id=None):
        if name is not None:
            if name in self.name_map:
                return self.name_map[name]
            else:
                raise ShipServiceError('{} is not exist in ship data'.format(name))
        elif wiki_id is not None:
            if wiki_id in self.wiki_id_map:
                return self.wiki_id_map[wiki_id]
            else:
                raise ShipServiceError('{} is not exist in ship data'.format(name))
        return self.ships

    @staticmethod
    def update():
        ships = KcwikiApi.ships()
        results = []
        max_id = 0
        for ship in ships:
            max_id = int(ship['id']) if int(ship['id']) > max_id else max_id
        for i in range(max_id + 1):
            results.append({})
        for ship in ships:
            _id = int(ship['id'])
            try:
                results[_id] = ship
            except IndexError:
                print(_id)
                print(ship)
        with open(path.join(data_dir, 'ship.json'), 'w') as f:
            json.dump(results, f)
        if results:
            echo.info('update ship data success!')
        else:
            echo.warn('no data')
            raise ShipServiceError('fetch ship data failed')
        return results


class ShipServiceError(Exception):
    pass