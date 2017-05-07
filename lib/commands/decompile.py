import click


@click.group()
def decompile_cmd():
    pass


@decompile_cmd.command('decompile')
@click.option('--src', '-s')
@click.option('--dst', '-d', default='./data/Core.decoded.swf')
def decompile(src, dst):
    """Decompile Core.swf"""
    if not src:
        print('Core.swf path is required.')
        return
    order = [0, 7, 2, 5, 4, 3, 6, 1]
    with open(src, 'rb') as f:
        org = f.read()
    with open(dst, 'wb') as dec:
        size = (len(org) - 128) >> 3
        dec.write(org[0:128])
        for i in order:
            dec.write(org[i*size+128: (i+1) * size + 128])
    click.echo('Done')

