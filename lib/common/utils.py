import click


class Echo(object):
    @staticmethod
    def info(message, **kwargs):
        click.echo(click.style(message, fg='green'), **kwargs)

    @staticmethod
    def error(message, **kwargs):
        click.echo(click.style(message, fg='red'), **kwargs)

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'