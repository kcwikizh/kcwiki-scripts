import os
import subprocess
import click
import requests


@click.group()
def decompile_cmd():
    pass


@decompile_cmd.command('decompile')
@click.option('--dst', '-d', default='./data/Core.decoded.swf')
def decompile(dst):
    """Decompile Core.swf"""
    r = requests.get('http://125.6.189.215/kcs/Core.swf')
    org = r.content
    order = [0, 7, 2, 5, 4, 3, 6, 1]
    with open(dst, 'wb') as dec:
        size = (len(org) - 128) >> 3
        dec.write(org[0:128])
        for i in order:
            dec.write(org[i*size+128: (i+1) * size + 128])
    click.echo('Done. Decoded file is at {}'.format(dst))


@decompile_cmd.command('battle:swf')
def get_battle_swf():
    """Download and extract BattleMain.swf"""
    work_dir = os.getcwd()
    click.echo('Downloading BattleMain.swf...')
    r = requests.get('http://203.104.209.71/kcs/scenes/BattleMain.swf')
    local_swf_path = '{}/data/BattleMain.swf'.format(work_dir)
    with open(local_swf_path, 'wb') as f:
        f.write(r.content)
    subprocess.call('rm -rf {}/data/decompiled'.format(work_dir), shell=True)
    ret = subprocess.call('ffdec.sh -export script "{}/data/decompiled"  {}/data/BattleMain.swf'.format(
        work_dir, work_dir),shell=True)
    if ret == 0:
        print('Required file is BattleConsts.as')
        subprocess.call('open {}/data/decompiled/scripts/battle'.format(work_dir), shell=True)
