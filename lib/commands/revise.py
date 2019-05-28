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
@click.option('--version', default='v3')
def revise_main(version='v3'):
    revise_service = ReviseService(version)
    revise_service.handle()


@revise_cmd.command(name="revise:test")
@click.option('--id', '-i')
def revice_test(id):
    if not id:
        print("Error: Argument 'ship id' is required")
        return
    revise_service = ReviseService()
    revise_service.test_voice(id)

