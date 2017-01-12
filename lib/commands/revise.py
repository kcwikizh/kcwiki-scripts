import click
from lib.services.voice import VoiceService
from lib.services.revise import ReviseService


@click.group()
def revise_cmd():
    pass


@revise_cmd.command(name="revise:download")
def revise_download_voice():
    voice_service = VoiceService()
    voice_service.download()


@revise_cmd.command(name="revise")
@click.option('--version', default='v2')
def revise_main(version='v2'):
    revise_service = ReviseService(version)
    revise_service.handle()


