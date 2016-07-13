#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=['update'])
    parser.add_argument("target", type=str)
    args = parser.parse_args()
    if args.action == 'update' and args.target == 'ship':
        from action.update.ship import UpdateShipAction
        ships = UpdateShipAction.get()
        if len(ships) > 0:
            print('update ship data success!')
        else:
            print('no data')
