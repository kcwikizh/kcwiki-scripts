import click


class Echo(object):
    @staticmethod
    def info(message, **kwargs):
        click.echo(click.style(message, fg='green'), **kwargs)

    @staticmethod
    def error(message, **kwargs):
        click.echo(click.style(message, fg='red'), **kwargs)
