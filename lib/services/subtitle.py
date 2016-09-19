import re
import json
import copy
from os import path
from moebot import MwApi
from .ship import ShipService
from lib.common.log import debug
from lib.common.config import CONFIG, DATA_DIR
from lib.common.utils import has_keys, Echo as echo


class SubtitleService(object):
    def __init__(self):
        super(SubtitleService, self).__init__()
        self.mw = MwApi('https://zh.kcwiki.moe/api.php')
        self.mw.login(CONFIG['account']['username'], CONFIG['account']['password'])
        self.ship_service = ShipService()
        self.ships = self.ship_service.get()
        self.ships = self.ships[:490]
        self.kaiship = self.ship_service.get_kai_set()
        self.subtitles = {'zh': {}, 'jp': {}, 'distinct': {'zh': {}, 'jp': {}}}
        self.missing = []

    def get(self, mode="all"):
        if mode == 'all':
            self.get_main()
            return self.get_seasonal()
        elif mode == 'seasonal':
            self.clean()
            return self.get_seasonal()
        elif mode == 'main':
            return self.get_main()
        else:
            raise SubtitleServiceError(
                'SubtitlesService.get has a invalid argument: type_({})'.format(mode))

    def get_main(self):
        """ 从各个舰娘词条中提取生成字幕数据(不含季节性) """
        self.clean()
        for ship in self.ships:
            self._handle(ship)
        return self.subtitles

    def get_by_ship(self, name):
        """ 提取特定舰娘的字幕数据(不含季节性) """
        self.clean()
        ship = self.ship_service.get(name=name)
        self._handle(ship)
        return self.subtitles

    def get_seasonal(self):
        self._handle_seasonal('季节性/2016年初秋季节', 'zh')
        self._handle_seasonal('季节性/2016年初秋季节', 'jp')
        return self.subtitles

    def clean(self):
        self.subtitles = {'zh': {}, 'jp': {}, 'distinct': {'zh': {}, 'jp': {}}}
        self.missing = []

    def _handle(self, ship):
        """ 抓取舰娘页面获取字幕数据的逻辑 """
        if not has_keys(ship, 'id', 'name', 'chinese_name') \
                or int(ship['id']) in self.kaiship:
            debug('skipped: {}'.format(ship))
            return
        title = ship['chinese_name']
        echo.info('正在获取【{}】页面'.format(title))
        content = self._get_wiki_content(title)
        results = self._post_process(content)
        if not results:
            message = '缺少【{}】的语音翻译'.format(title)
            echo.info(message)
            debug(message)
            self.missing.append(title)
            return
        self._generate_subtitles(results, ship, 'zh')
        results = self._post_process(content, 'jp')
        self._generate_subtitles(results, ship, 'jp')

    def _get_wiki_content(self, title):
        """ 获取指定舰娘的舰娘百科词条文本内容 """
        rep = self.mw.pageid(title, convert_titles='zh-cn', redirect=True)
        if not rep['success']:
            raise SubtitleServiceError('获取词条ID时, Mediawiki API 发生错误')
        pageid = list(rep['contents'].keys())[0]
        if int(pageid) == -1:
            raise SubtitleServiceError('页面【{}】不存在'.format(title))
        rep = self.mw.content(pid=pageid)
        if not rep['success']:
            raise SubtitleServiceError('获取词条内容时, Mediawiki API 发生错误')
        content = rep['contents'][pageid]['revisions'][0]['*']
        return content

    @staticmethod
    def _post_process(content, lang='zh'):
        """ 后处理,从舰娘百科词条中正则提取台词翻译 """
        results = []
        namemap = json.load(open(path.join(DATA_DIR, 'namemap.json'), 'r'))
        re_lang_map = {'zh': '中文译文', 'jp': '日文台词'}
        content = re.sub(r'<(.*)>.*?</\1>', '', content)
        content = re.sub(r'{{ruby-zh\|(.*?)\|(.*?)}}', r'\1(\2)', content)
        pattern = re.compile(r'\{\{台词翻译表(?:.|\n)*?档名\s*?=(.*?)\s*?\n(?:.|\n)*?' +
                             re_lang_map[lang] +
                             r'\s*?=([^\|\{\}]*?)(?:\|(?:.|\n)*?)?\}\}', re.MULTILINE)
        matches = re.findall(pattern, content)
        for m in matches:
            filename, quote = m
            if not filename or not quote or len(filename.split('-')) < 2:
                continue
            quote = re.sub(r'<br.*?>', '', quote)
            quote = re.sub(r'<(.*)>.*?</\1>', '', quote)
            quote = quote.replace('\n', '')
            no = filename.split('-')[0].strip()
            if filename.split('-')[1] in namemap:
                mp3 = namemap[filename.split('-')[1]]
            else:
                continue
            echo.info('{}, {}.mp3, {}'.format(no, mp3, quote))
            results.append((no, mp3, quote))
        return results

    def _generate_subtitles(self, results, ship, lang='zh'):
        """根据提取到的台词,转换(wiki id ==> ship id)生成台词字典"""
        subtitles = {}
        ship_id = int(ship['id'])
        sort_no = int(ship['sort_no'])
        after_ship_id = int(ship['after_ship_id'])
        for no, mp3, quote in results:
            if no.endswith('a'):
                continue
            if int(no) == sort_no:
                subtitles[mp3] = quote
        self.subtitles[lang][ship_id] = subtitles
        self.subtitles['distinct'][lang] = copy.copy(subtitles)
        if int(ship['after_ship_id']) <= 0:
            return
        ship_kai = self.ships[after_ship_id]
        ship_kai_id = int(ship_kai['id'])
        ship_kai_sort_no = int(ship_kai['sort_no'])
        subtitles_kai = subtitles.copy()
        self.subtitles['distinct'][lang][ship_kai_id] = {}
        echo.info('读取【{}】的翻译'.format(ship_kai['name']))
        for no, mp3, quote in results:
            if no.endswith('a') and int(no[:-1]) == sort_no \
                    or not no.endswith('a') and int(no) == ship_kai_sort_no:
                subtitles_kai[mp3] = quote
                self.subtitles['distinct'][lang][ship_kai_id][mp3] = quote
        self.subtitles[lang][ship_kai_id] = subtitles_kai
        ship_kai_after_ship_id = int(ship_kai['after_ship_id'])
        while ship_kai_after_ship_id > 0 and \
                ship_kai_after_ship_id not in self.subtitles[lang]:
            ship_kai = self.ships[ship_kai_after_ship_id]
            ship_kai_id = int(ship_kai['id'])
            ship_kai_sort_no = int(ship_kai['sort_no'])
            ship_kai_after_ship_id = int(ship_kai['after_ship_id'])
            subtitles_kai = subtitles_kai.copy()
            self.subtitles['distinct'][lang][ship_kai_id] = {}
            echo.info('读取【{}】的翻译'.format(ship_kai['name']))
            for no, mp3, quote in results:
                if no.endswith('a'):
                    continue
                if int(no) == ship_kai_sort_no:
                    subtitles_kai[mp3] = quote
                    self.subtitles['distinct'][lang][mp3] = quote
                self.subtitles[lang][ship_kai_id] = subtitles_kai

    def _handle_seasonal(self, title, lang):
        """ 抓取季节性页面获取字幕数据的逻辑 """
        content = self._get_wiki_content(title)
        results = self._post_process_seasonal(content, lang)
        echo.info('Total ships that have seasonal quotes({}): {}'.format(lang, len(results)))
        for wiki_id, quote, voice_no in results:
            ship = self.ship_service.get(wiki_id=wiki_id.strip())
            ship_id = int(ship['id'])
            name = ship['name']
            after_ship_id = int(ship['after_ship_id'])
            echo.info('{} {} {} {}'.format(ship_id, name, quote, voice_no))
            if ship_id not in self.subtitles[lang]:
                self.subtitles[lang][ship_id] = {}
            self.subtitles[lang][ship_id][voice_no] = quote
            loop_count = 0
            while after_ship_id > 0 and loop_count < 10:
                loop_count += 1
                ship = self.ships[after_ship_id]
                ship_id = int(ship['id'])
                after_ship_id = int(ship['after_ship_id'])
                if ship_id not in self.subtitles[lang]:
                    self.subtitles[lang][ship_id] = {}
                self.subtitles[lang][ship_id][voice_no] = quote

    @staticmethod
    def _post_process_seasonal(content, lang='zh'):
        """ 季节性字幕的后处理 """
        content = re.sub(r'<(.*)>.*?</\1>', '', content)
        content = re.sub(r'{{ruby-zh\|(.*?)\|(.*?)}}', r'\1(\2)', content)
        re_lang_map = {'zh': '中文译文', 'jp': '日文台词'}
        pattern = re.compile(r'\{\{台词翻译表(?:.|\n)*?档名\s*?=(.*?)\s*?\n(?:.|\n)*?' +
                             re_lang_map[lang] +
                             r'\s*?=([^\|\{\}]*?)(?:\|(?:.|\n)*?)?\}\}', re.MULTILINE)
        matches = re.findall(pattern, content)
        results = []
        for m in matches:
            filename, quote = m
            if not filename or not quote or len(filename.split('-')) < 2:
                continue
            quote = re.sub(r'<br.*?>', '', quote).strip()
            quote = re.sub(r'<(.*)>.*?</\1>', '', quote)
            no = filename.split('-')[0]
            namemap = json.load(open(path.join(DATA_DIR, 'namemap.json'), 'r'))
            pattern = re.compile(r'({})'.format('|'.join(namemap.keys())))
            voice = re.findall(pattern, filename)
            if len(voice) < 1:
                message = '季节性档名异常，档名：{}'.format(filename)
                debug(message)
                echo.error(message)
                voice_no = 2
            else:
                voice_no = namemap[voice[0]]
            results.append((no, quote, voice_no))
        return results


class SubtitleServiceError(Exception):
    pass
