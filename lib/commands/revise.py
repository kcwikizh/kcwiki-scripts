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
def revise_main():
    revise_service = ReviseService()
    revise_service.handle()


