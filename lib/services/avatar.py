import json
import os
import datetime
from glob import glob
from io import BytesIO
from pyquery import PyQuery as pq
import requests
from moebot import MwApi
from PIL import Image
from weibo import Client

from lib.common.config import CONFIG
from lib.common.utils import Echo as echo

AVATAR_CONFIG_MAP = {
    # https://developer.twitter.com/en/docs/twitter-api/v1/accounts-and-users/follow-search-get-users/api-reference/get-users-show
    'api': 'https://api.twitter.com/1.1/users/show.json',
    'kancolle': {
        'screen_name': CONFIG['twitter']['kancolle_screen_name'],
        'twitter_nickname': '「艦これ」開発/運営',
        'filename': 'KanColleStaffAvatar',
        'thumbname': 'KanColleStaffAvatarThumb'
    },
    'c2': {
        'screen_name': CONFIG['twitter']['c2_screen_name'],
        'twitter_nickname': 'C2機関',
        'filename': 'C2StaffAvatar',
        'thumbname': 'C2StaffAvatarThumb'
    }
}



class AvatarService(object):
    @staticmethod
    def do(src='kancolle'):
        SAVE_DIR = CONFIG['twitter']['save_dir']
        DUPLI_SAVE_DIR = CONFIG['twitter']['dupli_dir']
        BEARER_TOKEN = CONFIG['twitter']['bearer_token']
        SCREEN_NAME = CONFIG[src]['screen_name']
        FILE_NAME = AVATAR_CONFIG_MAP[src]['filename']
        THUMB_NAME = AVATAR_CONFIG_MAP[src]['thumbname']
        params = {'screen_name': SCREEN_NAME}
        headers = {
            'authorization': 'authorization: Bearer {}'.format(BEARER_TOKEN)
        }
        content = requests.get(
            AVATAR_CONFIG_MAP['api'], params=params, headers=headers).text
        avatar_url = json.loads(content).get('profile_image_url_https')
        if not avatar_url or not isinstance(avatar_url, str):
            echo.error('Can not find {} avatar'.format(SCREEN_NAME))
            return
        if not isinstance(avatar_url, str):
            echo.error('Unexpected  avatar url {}'.format(avatar_url))
            return

        # ref: https://developer.twitter.com/en/docs/accounts-and-users/user-profile-images-and-banners
        # remove '_normal' from avatar_url
        # example
        # from http://pbs.twimg.com/profile_images/1327246587685269504/RElBPPS-_normal.png
        # to http://pbs.twimg.com/profile_images/1327246587685269504/RElBPPS-.png
        url_segments = avatar_url.split('_normal')
        if len(url_segments) != 2:
            echo.error('Unexpected avatar url: {}'.format(avatar_url))
            return
        original_avatar_url = url_segments[0] + url_segments[1]
        # backward compatible
        # TODO remove avatar_thumb_url?
        avatar_thumb_url = avatar_url
        del avatar_url
        echo.info('Twitter avatar url: 【{}】'.format(original_avatar_url))

        if original_avatar_url:
            # 解析推特头像、缩略图
            image = Image.open(
                BytesIO(requests.get(original_avatar_url).content))
            imageThumb = Image.open(
                BytesIO(requests.get(avatar_thumb_url).content))
            suffix = 'png'
            oriname = original_avatar_url.split('/')[-1].split('.')[0]
            today = datetime.datetime.now().strftime('%Y%m%d%H%M')
            path = ''.join([DUPLI_SAVE_DIR, '/', oriname, '.', suffix])
            image_url_path = ''.join([SAVE_DIR, '/', 'image_url.txt'])
            image_url = ''.join(['http://static.kcwiki.moe/Avatar/',
                                 oriname, 'Thumb.', suffix])
            avatar_updated_flag = False
            # 检测头像是否更新，如果没有更新，不进行存取操作
            if os.path.exists(path):
                echo.info("Current avatar is newest.")
                if not os.path.exists(image_url_path):
                    with open(image_url_path, 'w') as f:
                        f.write(image_url)
            else:
                # 存取头像到指定目录
                echo.info("Saving avatar...")
                AvatarService._save(image, DUPLI_SAVE_DIR, FILE_NAME + today, suffix)
                avatar_updated_flag = True
                with open(image_url_path, 'w') as f:
                    f.write(image_url)
                requests.get('http://api.kcwiki.moe/purge/avatar')
            AvatarService._save(image, SAVE_DIR, FILE_NAME, suffix)
            AvatarService._save(imageThumb, SAVE_DIR, THUMB_NAME, suffix)
            AvatarService._save(image, DUPLI_SAVE_DIR, oriname, suffix)
            AvatarService._save(image, DUPLI_SAVE_DIR, oriname + 'Thumb', suffix)
            # 上传头像到Kcwiki
            if CONFIG['env'] != 'local' and src == 'kancolle':
                pathTimestamp = ''.join([DUPLI_SAVE_DIR, '/',
                                         oriname, '.', suffix])
                filename = ''.join([FILE_NAME, today, '.', suffix])
                rep = AvatarService._upload(pathTimestamp, filename)
            if avatar_updated_flag:
                echo.info('微博更新头像……')
                AvatarService.weibo_share(''.join([SAVE_DIR, '/', FILE_NAME, '.', suffix]), src)
            archives = [x.split('/')[-1] for x in list(glob("{}/KanColleStaffAvatar*.png".format(DUPLI_SAVE_DIR)))]
            archives = sorted(archives)
            json.dump(archives, open('{}/archives.json'.format(DUPLI_SAVE_DIR), 'w'))
        else:
            echo.error('Can not find kancolle_staff avatar')

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
        echo.info('正在上传头像图片...')
        return mw.upload(filepath, filename)

    @staticmethod
    def weibo_share(image_path, src):
        weibo = CONFIG['weibo']
        weibo_client = Client(weibo['api_key'], weibo['api_secret'], weibo['redirect_url'],
                              username=weibo['username'], password=weibo['password'])
        with open(image_path, 'rb') as pic:
            resp = weibo_client.post('statuses/share', status='{} 头像更新 https://zh.kcwiki.org'.format(AVATAR_CONFIG_MAP[src]['twitter_nickname']), pic=pic)
            with open('/tmp/weibo_post_status.log', 'w') as fd:
                fd.write(json.dumps(resp))


