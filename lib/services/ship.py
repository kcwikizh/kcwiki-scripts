import json
from os import path
from .api import KcwikiApi
from ..common.config import DATA_DIR
from ..common.utils import has_keys, Echo as echo


class ShipService(object):
    def __init__(self):
        ship_path = path.join(DATA_DIR, 'ship.json')
        if path.exists(ship_path):
            self.ships = json.load(open(ship_path, 'r'))
        else:
            echo.info('"ship.json" is not exist, fetch ship data now..')
            self.ships = ShipService.update()
        self.ships = self.ships[:1501]
        self.name_map = {}
        self.wiki_id_map = {}
        self.sort_no_map = {}
        for ship in self.ships:
            if has_keys(ship, 'name'):
                self.name_map[ship['name']] = ship
            if has_keys(ship, 'chinese_name'):
                self.name_map[ship['chinese_name']] = ship
            if has_keys(ship, 'wiki_id'):
                self.wiki_id_map[ship['wiki_id']] = ship
            if has_keys(ship, 'sort_no'):
                self.sort_no_map[ship['sort_no']] = ship

    def get_kai_set(self):
        """获取已改船的集合"""
        ships = self.ships
        kaiship = set()
        for ship in ships:
            if has_keys(ship, 'after_ship_id') and ship['after_ship_id'] is not None:
                kaiship.add(int(ship['after_ship_id']))
        return kaiship

    def get_origin_set(self):
        """获取未改船集合"""
        all_ship_set = set([ship['id'] for ship in self.ships if has_keys(ship, 'id', 'wiki_id')])
        kai_ship_set = self.get_kai_set()
        return all_ship_set - kai_ship_set

    def get(self, name=None, wiki_id=None, sort_no=None):
        if name is not None:
            if name in self.name_map:
                return self.name_map[name]
            else:
                raise ShipServiceError('Ship "{}" not found'.format(name))
        elif wiki_id is not None:
            if wiki_id in self.wiki_id_map:
                return self.wiki_id_map[wiki_id]
            else:
                raise ShipServiceError('Ship (wiki id: {}) not found'.format(wiki_id))
        elif sort_no is not None:
            if sort_no in self.sort_no_map:
                return self.sort_no_map[sort_no]
            else:
                raise ShipServiceError('Ship (sort no: {}) not found'.format(sort_no))
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
        with open(path.join(DATA_DIR, 'ship.json'), 'w') as f:
            json.dump(results, f)
        if results:
            echo.info('update ship data success!')
        else:
            echo.warn('no data')
            raise ShipServiceError('fetch ship data failed')
        return results


class ShipServiceError(Exception):
    pass