import json
import os
import datetime
from glob import glob
from io import BytesIO
from pyquery import PyQuery as pq
import click
import requests
from moebot import MwApi
from PIL import Image

from lib.common.config import CONFIG


class AvatarService(object):
    @staticmethod
    def do():
        SAVE_DIR = CONFIG['twitter']['save_dir']
        DUPLI_SAVE_DIR = CONFIG['twitter']['dupli_dir']
        FILE_NAME = 'KanColleStaffAvatar'
        THUMB_NAME = 'KanColleStaffAvatarThumb'

        content = requests.get(CONFIG['twitter']['url']).content
        avatar = pq(content)('.ProfileAvatar-image')
        avatar_thumb = pq(content)('.stream-item-header .avatar')[0]
        click.echo('Twitter avatar url: 【{}】'.format(avatar.attr('src')))
        click.echo('Twitter avatar thumbnail url: 【{}】'.format(avatar_thumb.get('src')))
        if avatar:
            # 解析推特头像、缩略图
            image = Image.open(BytesIO(requests.get(avatar.attr('src')).content))
            imageThumb = Image.open(BytesIO(requests.get(avatar_thumb.get('src')).content))
            suffix = 'png'
            oriname = avatar.attr('src').split('/')[-1].split('.')[0]
            today = datetime.datetime.now().strftime('%Y%m%d%H%M')
            path = ''.join([DUPLI_SAVE_DIR, '/', oriname, '.', suffix])
            image_url_path = ''.join([SAVE_DIR, '/', 'image_url.txt'])
            image_url = ''.join(['http://static.kcwiki.moe/Avatar/',
                                 oriname, 'Thumb.', suffix])
            # 检测头像是否更新，如果没有更新，不进行存取操作
            if os.path.exists(path):
                click.echo("Current avatar is newest.")
                if not os.path.exists(image_url_path):
                    with open(image_url_path, 'w') as f:
                        f.write(image_url)
            else:
                # 存取头像到指定目录
                click.echo("Saving avatar...")
                AvatarService._save(image, DUPLI_SAVE_DIR, FILE_NAME + today, suffix)
                with open(image_url_path, 'w') as f:
                    f.write(image_url)
                requests.get('http://api.kcwiki.moe/purge/avatar')
            AvatarService._save(image, SAVE_DIR, FILE_NAME, suffix)
            AvatarService._save(imageThumb, SAVE_DIR, THUMB_NAME, suffix)
            AvatarService._save(image, DUPLI_SAVE_DIR, oriname, suffix)
            AvatarService._save(image, DUPLI_SAVE_DIR, oriname + 'Thumb', suffix)
            # 上传头像到Kcwiki
            pathTimestamp = ''.join([DUPLI_SAVE_DIR, '/',
                                     oriname, '.', suffix])
            filename = ''.join([FILE_NAME, today, '.', suffix])
            AvatarService._upload(pathTimestamp, filename)
            archives = [x.split('/')[-1] for x in list(glob("{}/KanColleStaffAvatar*.png".format(DUPLI_SAVE_DIR)))]
            archives = sorted(archives)
            json.dump(archives, open('{}/archives.json'.format(DUPLI_SAVE_DIR), 'w'))
        else:
            click.echo('Can not find kancolle_staff avatar')

    @staticmethod
    def _save(image, dir_, name, suffix):
        path = ''.join([dir_, '/', name, '.', suffix])
        if os.path.exists(path):
            os.remove(path)
        image.save(path)
        os.chmod(path, 0o644)

    @staticmethod
    def _upload(filepath, filename):
        mw = MwApi(CONFIG['wiki_url'], limit=500)
        username = CONFIG['account']['username']
        password = CONFIG['account']['password']
        mw.login(username, password)
        click.echo(u'正在上传头像图片...')
        mw.upload(filepath, filename)

