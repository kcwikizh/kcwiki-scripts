#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
from lib.commands.update import update_cmd
from lib.commands.fetch import fetch_cmd
from lib.commands.plan import plan_cmd
from lib.commands.revise import revise_cmd
from lib.commands.common import common_cmd


cli = click.CommandCollection(sources=[update_cmd, fetch_cmd, plan_cmd, revise_cmd, common_cmd])

if __name__ == '__main__':
    cli()
