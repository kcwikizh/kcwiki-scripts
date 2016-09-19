import itertools
import os
import time
import traceback
import requests
from multiprocessing.dummy import Pool as ThreadPool
from lib.services.ship import ShipService
from lib.common.config import CONFIG
from lib.common.utils import has_keys, convert_voice_filename, Echo as echo


class VoiceService(object):
    def __init__(self):
        super(VoiceService, self).__init__()
        self.total = 0
        self.counter = itertools.count()
        self.ship_service = ShipService()
        self.ships = self.ship_service.get()
        self.root = CONFIG['voice_cache']

    def download(self):
        queue = []
        for ship in self.ships:
            if has_keys(ship, 'filename', 'sort_no') and ship['sort_no'] > 0:
                ship_id = ship['id']
                ship_filename = ship['filename']
                voice_dir = os.path.join(self.root, 'sound/kc{}/'.format(ship_filename))
                if not os.path.exists(voice_dir):
                    os.makedirs(voice_dir)
                for i in range(53):
                    voice_id = convert_voice_filename(ship_id, i+1)
                    url = 'http://125.6.189.215/kcs/sound/kc{}/{}.mp3'.format(ship_filename, voice_id)
                    queue.append(url)
        self.total = len(queue)
        pool = ThreadPool(1)
        pool.map(self.download_worker, queue)
        echo.info('End.')

    def download_worker(self, url):
        voice_path = os.path.join(self.root, url.split('kcs/')[-1])
        value = next(self.counter)
        retries = 0
        while retries < 5:
            echo.info('{} TRY!'.format(url))
            try:
                rep = requests.get(url, stream=True)
                if rep.status_code == 200:
                    echo.info('{} HIT! ({}/{})'.format(url, value+1, self.total))
                    with open(voice_path, 'wb') as f:
                        for chunk in rep.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                else:
                    echo.error('{} {} ({}/{})'.format(url, rep.status_code, value+1, self.total))
                break
            except Exception as e:
                if isinstance(e, KeyboardInterrupt):
                    raise e
                retries += 1
                echo.error(e.message)
                traceback.print_exc()
                time.sleep(5)





