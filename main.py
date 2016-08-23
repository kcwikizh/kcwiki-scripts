#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
from lib.commands.update import update_cmd


cli = click.CommandCollection(sources=[update_cmd])

if __name__ == '__main__':
    cli()
