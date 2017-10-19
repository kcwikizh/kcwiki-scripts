import schedule
import click
import time
import traceback

from lib.commands.update import update_ships
from lib.services.revise import ReviseService
from lib.commands.fetch import fetch_start2_ooi, command_fetch_twitter_info
from ..common.utils import Echo as echo
from lib.services.subtitle import SubtitleService


@click.group()
def plan_cmd():
    pass


@plan_cmd.command(name='plan')
@click.pass_context
def plan(ctx):
    """job scheduling"""
    fetch_start2_ooi()
    schedule.every().hour.do(fetch_start2_ooi)
    schedule.every().hour.do(update_ships)
    schedule.every().day.at('05:00').do(task_update_subtitle)
    schedule.every().hour.do(command_fetch_twitter_info)
    schedule.every().hour.do(task_revise)
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            if isinstance(e, KeyboardInterrupt):
                echo.warn('aborted.')
                return
            traceback.print_exc()
        time.sleep(5)


def task_update_subtitle():
    service = SubtitleService()
    service.deploy()


def task_revise():
    service = ReviseService('v3', False)
    service.handle()
