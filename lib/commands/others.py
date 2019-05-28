import click


@click.group()
def others_cmd():
    pass


@others_cmd.command(name='debug')
def cmd_debug():
    """Local debugging"""
    from lib.services.subtitle import EnglishSubtitleParser
    parser = EnglishSubtitleParser()
    mode = 'all'
    if mode == 'page':
        import json
        with open('data/name.en.json', 'r') as fd:
            name_map = json.load(fd)
        parser.en_name_map = {int(k): v for k, v in name_map.items()}
        parser.parse_ship_page(233, 'Saratoga', '/wiki/Saratoga')
    else:
        parser.perform()
