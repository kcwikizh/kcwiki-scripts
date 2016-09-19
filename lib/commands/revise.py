import click
from lib.services.voice import VoiceService


@click.group()
def revise_cmd():
    pass


@revise_cmd.command(name="revise:download")
def revise_download_voice():
    voice_service = VoiceService()
    voice_service.download()

