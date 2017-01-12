import json
from os import path
from hashlib import md5
from lib.services.ship import ShipService
from lib.services.subtitle import SubtitleService
from lib.common.utils import has_keys, convert_voice_filename, Echo as echo
from lib.common.config import CONFIG, DATA_DIR


class ReviseService(object):
    def __init__(self, version='v2'):
        ship_service = ShipService()
        self.ships = ship_service.get()[:500]
        subtitle_service = SubtitleService()
        self.subtitles = subtitle_service.get('cache')
        self.version = version
        self.voice_path = path.join(CONFIG['voice_cache'], 'sound')
        self.data_path = CONFIG['revise'][version]['data']

    def handle(self):
        version = self.version
        voice_path = self.voice_path
        data_path = self.data_path
        results = {}
        for ship in self.ships:
            if not has_keys(ship, 'filename', 'sort_no') or ship['sort_no'] <= 0:
                continue
            ship_id = int(ship['id'])
            name = ship['name']
            filename = ship['filename']
            result = {
                'shipId': ship_id, 'shipName': name,
                'filename': filename, 'zh': {}, 'jp': {}, 'url': {}
            }
            for i in range(53):
                voice_id = convert_voice_filename(ship_id, i+1)
                url = CONFIG['revise'][version]['url'].format(filename, voice_id)
                mp3_path = '{}kc{}/{}.mp3'.format(voice_path, filename, voice_id)
                # 排除苍蓝语音
                if i+1 >= 30 and ship_id in [181, 182, 183]:
                    continue
                if path.exists(mp3_path):
                    if str(ship_id) in self.subtitles['zh'] and str(i+1) in self.subtitles['zh'][str(ship_id)]:
                        result['zh'][i+1] = self.subtitles['zh'][str(ship_id)][str(i+1)]
                    else:
                        result['zh'][i+1] = ''
                    if str(ship_id) in self.subtitles['jp'] and str(i+1) in self.subtitles['jp'][str(ship_id)]:
                        result['jp'][i + 1] = self.subtitles['jp'][str(ship_id)][str(i + 1)]
                    else:
                        result['jp'][i+1] = ''
                    result['url'][i+1] = url
            results[ship_id] = result
            json.dump(result, open(path.join(data_path, '{}.json'.format(ship_id)), 'w'))
        json.dump(results, open(path.join(DATA_DIR, 'revise.json'), 'w'))
        for ship in self.ships:
            if not has_keys(ship, 'name', 'after_ship_id'):
                continue
            name = ship['name']
            after_ship_id = int(ship['after_ship_id'])
            if name.find('改二甲') >= 0 or name.find('改二乙') >= 0 or after_ship_id <= 0:
                continue
            src_id = int(ship['id'])
            dst_id = after_ship_id
            self._diff(src_id, dst_id)

    def _diff(self, src_id, dst_id):
        version = self.version
        data_path = CONFIG['revise'][version]['data']
        src_path = path.join(data_path, '{}.json'.format(src_id))
        src_data = json.load(open(src_path, 'r'))
        dst_path = path.join(data_path, '{}.json'.format(dst_id))
        dst_data = json.load(open(dst_path, 'r'))
        voice_ids = dst_data['url'].keys()
        for voice_id in voice_ids:
            voice_id_str = str(voice_id)
            if voice_id_str not in src_data['url'] or voice_id_str not in dst_data['url']:
                continue
            src_url = src_data['url'][voice_id_str]
            dst_url = dst_data['url'][voice_id_str]
            src_md5 = self._md5(voice_id, src_url)
            dst_md5 = self._md5(voice_id, dst_url)
            if src_md5 != dst_md5 and len(src_md5) * len(dst_md5) > 0:
                echo.info('{} {} - {}'.format(voice_id, src_md5, dst_md5))
            else:
                if not has_keys(dst_data, 'same'):
                    dst_data['same'] = {}
                dst_data['same'][voice_id_str] = True
        json.dump(dst_data, open(dst_path, 'w'))

    def _md5(self, voice_id, url):
        voice_path = self.voice_path
        relative_path = url.split('/sound/')[-1]
        absolute_path = path.join(voice_path, relative_path)
        if path.exists(absolute_path):
            m = md5()
            m.update(open(absolute_path, 'rb').read())
            return m.hexdigest()
        else:
            raise ReviseServiceAction('{} {} not exist!!!'.format(voice_id, url))


class ReviseServiceAction(Exception):
    pass
