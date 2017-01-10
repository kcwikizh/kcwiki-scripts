import click


class Echo(object):
    @staticmethod
    def info(message, **kwargs):
        click.echo(click.style(message, fg='green'), **kwargs)

    @staticmethod
    def error(message, **kwargs):
        click.echo(click.style(message, fg='red'), **kwargs)

    @staticmethod
    def warn(message, **kwargs):
        click.echo(click.style(message, fg='red'), **kwargs)


def has_keys(dictionary, *args):
    if not dictionary:
        return False
    for key in args:
        if key not in dictionary:
            return False
    return True

vcKey = [604825, 607300, 613847, 615318, 624009, 631856, 635451, 637218,
         640529, 643036, 652687, 658008, 662481, 669598, 675545, 685034,
         687703, 696444, 702593, 703894, 711191, 714166, 720579, 728970,
         738675, 740918, 743009, 747240, 750347, 759846, 764051, 770064,
         773457, 779858, 786843, 790526, 799973, 803260, 808441, 816028,
         825381, 827516, 832463, 837868, 843091, 852548, 858315, 867580,
         875771, 879698, 882759, 885564, 888837, 896168]


def convert_voice_filename(ship_id, voice_id):
    return (ship_id + 7) * 17 * (vcKey[voice_id] - vcKey[voice_id - 1])\
        % 99173 + 100000

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'
