import re
import json
import copy
import datetime
from shutil import copyfile
from os import path
from collections import defaultdict

import click
from moebot import MwApi
import requests
from pyquery import PyQuery as pq
from .ship import ShipService
from lib.common.log import debug
from lib.common.config import CONFIG, DATA_DIR
from lib.common.constants import EN_SYMBOL_TO_VOICE_ID
from lib.common.utils import has_keys, Echo as echo, json_pretty_dump


class SubtitleService(object):
    def __init__(self):
        super(SubtitleService, self).__init__()
        self.mw = MwApi(CONFIG['wiki_url'])
        self.mw.login(CONFIG['account']['username'], CONFIG['account']['password'])
        self.ship_service = ShipService()
        self.english_parser = EnglishSubtitleParser()
        self.ships = self.ship_service.get()
        self.ships = self.ships[:800]
        self.kaiship = self.ship_service.get_kai_set()
        self.subtitles = self._get_data_struct()
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
        elif mode == 'cache':
            return self.get_cache()
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
        pages = CONFIG['quote_seasonal_page']
        for page in pages:
            self._handle_seasonal(page, 'zh')
            self._handle_seasonal(page, 'jp')
        self._convert_to_traditional()
        if CONFIG['subtitle']['english']:
            self.subtitles['en'] = self.english_parser.perform()
        return self.subtitles

    def get_cache(self):
        self.clean()
        self.subtitles = self._get_data_struct()
        self.subtitles['zh'] = json.load(open(path.join(DATA_DIR, 'subtitles.json'), 'r'))
        self.subtitles['jp'] = json.load(open(path.join(DATA_DIR, 'subtitlesJP.json'), 'r'))
        self.subtitles['distinct'] = json.load(open(path.join(DATA_DIR, 'subtitles_distinct.json'), 'r'))
        self.subtitles['seasonal'] = json.load(open(path.join(DATA_DIR, 'subtitles_seasonal.json'), 'r'))
        return self.subtitles

    def clean(self):
        self.subtitles = self._get_data_struct()
        self.missing = []

    def _handle(self, ship):
        """ 抓取舰娘页面获取字幕数据的逻辑 """
        if not has_keys(ship, 'id', 'name', 'chinese_name', 'wiki_id') \
                or int(ship['id']) in self.kaiship or ship['wiki_id'] is None:
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

    def deploy(self):
        subtitles = self.get()
        now = datetime.datetime.now().strftime('%Y%m%d%H')
        subtitles['zh']['version'] = now
        subtitles['jp']['version'] = now
        subtitles['tw']['version'] = now
        subtitles['en']['version'] = now
        json.dump(subtitles['zh'], open(path.join(DATA_DIR, 'subtitles.json'), 'w'))
        json.dump(subtitles['jp'], open(path.join(DATA_DIR, 'subtitlesJP.json'), 'w'))
        json.dump(subtitles['tw'], open(path.join(DATA_DIR, 'subtitlesTW.json'), 'w'))
        if CONFIG['subtitle']['english']:
            json.dump(subtitles['en'], open(path.join(DATA_DIR, 'subtitlesEN.json'), 'w'))
        json.dump(subtitles['distinct'], open(path.join(DATA_DIR, 'subtitles_distinct.json'), 'w'))
        json.dump(subtitles['seasonal'], open(path.join(DATA_DIR, 'subtitles_seasonal.json'), 'w'))
        env = CONFIG['env']
        deploy_filename = now + '.json'
        deploy_dir = CONFIG[env]['subtitle']
        copyfile(path.join(DATA_DIR, 'subtitles.json'), path.join(deploy_dir, 'zh-cn', deploy_filename))
        copyfile(path.join(DATA_DIR, 'subtitlesJP.json'), path.join(deploy_dir, 'jp', deploy_filename))
        copyfile(path.join(DATA_DIR, 'subtitlesTW.json'), path.join(deploy_dir, 'zh-tw', deploy_filename))
        if CONFIG['subtitle']['english']:
            copyfile(path.join(DATA_DIR, 'subtitlesEN.json'), path.join(deploy_dir, 'en', deploy_filename))
        copyfile(path.join(DATA_DIR, 'subtitles_distinct.json'), path.join(deploy_dir, 'subtitles_distinct.json'))
        copyfile(path.join(DATA_DIR, 'subtitles_seasonal.json'), path.join(deploy_dir, 'subtitles_seasonal.json'))
        meta_file = path.join(deploy_dir, 'meta.json')
        meta = json.load(open(meta_file, 'r'))
        meta['latest'] = deploy_filename[:-5]
        json.dump(meta, open(meta_file, 'w'))
        # Purge cache in api.kcwiki.moe
        requests.get('http://api.kcwiki.moe/purge/subtitles')

    @staticmethod
    def _post_process(content, lang='zh'):
        """ 后处理,从舰娘百科词条中正则提取台词翻译 """
        results = []
        namemap = json.load(open(path.join(DATA_DIR, 'namemap.json'), 'r'))
        re_lang_map = {'zh': '中文译文', 'jp': '日文台词'}
        content = re.sub(r'<(.*)>.*?</\1>', '', content)
        content = re.sub(r'<.*?/>', '', content)
        content = re.sub(r'<.*?>', '', content)
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
            if not quote.strip():
                quote = 'このサブタイトルに対応するサブタイトルがありません！艦これ中国語ウィキ（https://zh.kcwiki.moe/）に参加して、この内容を一緒に完成しましょう！' if lang == 'jp' else '本字幕暂时没有翻译 请到舰娘百科(https://zh.kcwiki.moe/)协助我们翻译'
            no = filename.split('-')[0].strip()
            if filename.split('-')[1] in namemap:
                mp3 = namemap[filename.split('-')[1]]
            else:
                continue
            if CONFIG['debug']:
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
        self.subtitles['distinct'][lang][ship_id] = copy.copy(subtitles)
        if int(ship['after_ship_id']) <= 0:
            return
        ship_kai = self.ships[after_ship_id]
        ship_kai_id = int(ship_kai['id'])
        ship_kai_wiki_id = ship_kai['wiki_id']
        subtitles_kai = subtitles.copy()
        self.subtitles['distinct'][lang][ship_kai_id] = {}
        echo.info('读取【{}】的翻译'.format(ship_kai['name']))
        for no, mp3, quote in results:
            if ship_kai_wiki_id == str(no):
                subtitles_kai[mp3] = quote
                self.subtitles['distinct'][lang][ship_kai_id][mp3] = quote
        self.subtitles[lang][ship_kai_id] = subtitles_kai
        ship_kai_after_ship_id = int(ship_kai['after_ship_id'])
        while ship_kai_after_ship_id > 0 and \
                ship_kai_after_ship_id not in self.subtitles[lang]:
            ship_kai = self.ships[ship_kai_after_ship_id]
            ship_kai_id = int(ship_kai['id'])
            ship_kai_after_ship_id = int(ship_kai['after_ship_id'])
            ship_kai_wiki_id = ship_kai['wiki_id']
            subtitles_kai = subtitles_kai.copy()
            self.subtitles['distinct'][lang][ship_kai_id] = {}
            echo.info('读取【{}】的翻译'.format(ship_kai['name']))
            for no, mp3, quote in results:
                if ship_kai_wiki_id == str(no):
                    subtitles_kai[mp3] = quote
                    self.subtitles['distinct'][lang][ship_kai_id][mp3] = quote
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
            if CONFIG['debug']:
                echo.info('{} {} {} {}'.format(ship_id, name, quote, voice_no))
            self._set_quote(self.subtitles, lang, ship_id, voice_no, quote)
            self._set_quote(self.subtitles['seasonal'], lang, ship_id, voice_no, quote)
            loop_count = 0
            while after_ship_id > 0 and loop_count < 10:
                loop_count += 1
                ship = self.ships[after_ship_id]
                ship_id = int(ship['id'])
                after_ship_id = int(ship['after_ship_id'])
                self._set_quote(self.subtitles, lang, ship_id, voice_no, quote)

    @staticmethod
    def _post_process_seasonal(content, lang='zh'):
        """ 季节性字幕的后处理 """
        content = re.sub(r'<(.*)>.*?</\1>', '', content)
        content = re.sub(r'<.*?/>', '', content)
        content = re.sub(r'<.*?>', '', content)
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
            if not quote.strip():
                quote = 'このサブタイトルに対応するサブタイトルがありません！艦これ中国語ウィキ（https://zh.kcwiki.moe/）に参加して、この内容を一緒に完成しましょう！' if lang == 'jp' else '本字幕暂时没有翻译 请到舰娘百科(https://zh.kcwiki.moe/)协助我们翻译'
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

    def _convert_to_traditional(self):
        text = json.dumps(self.subtitles['zh'], ensure_ascii=False)
        url = CONFIG['wiki_url']
        payload = {
            'action': 'parse', 'contentmodel': 'wikitext',
            'format': 'json', 'uselang': 'zh-tw', 'text': text
        }
        rep = requests.post(url, payload)
        if rep.ok:
            text = rep.json()['parse']['text']['*']
            match = re.search(r'<p>(.*?)</p>', text, re.DOTALL)
            if match:
                content = match.group(1).strip()
            else:
                raise SubtitleServiceError('convert_to_traditional: extract converted data failed')
            content = re.sub(r'<.*?/>', '', content)
            content = re.sub(r'<.*?>', '', content)
            self.subtitles['tw'] = json.loads(content)
        else:
            raise SubtitleServiceError('Fetch traditional converted data failed: {}'.format(rep.status_code))

    @staticmethod
    def _set_quote(subtitles, lang, ship_id, voice_no, quote):
        if ship_id not in subtitles[lang]:
            subtitles[lang][ship_id] = {}
        subtitles[lang][ship_id][voice_no] = quote

    @staticmethod
    def _get_data_struct():
        return {'zh': {}, 'jp': {}, 'tw': {}, 'en': {}, 'distinct': {'zh': {}, 'jp': {}}, 'seasonal': {'zh': {}, 'jp': {}}}


class EnglishSubtitleParser(object):
    def __init__(self):
        super(EnglishSubtitleParser, self).__init__()
        self.host = 'http://kancolle.wikia.com'
        self.content = ''
        self.ship_list_url = self.host + '/wiki/Ship_list'
        self.ship_service = ShipService()
        self.ships = self.ship_service.ships
        self.ship = None
        self.subtitles = defaultdict(dict)
        self.en_name_map = {}
        self.kai_map = {}
        self.nth = 0

    def perform(self):
        origin_sortno_set = [self.ships[_id]['sort_no'] for _id in self.ship_service.get_origin_set()]
        rep = requests.get(self.ship_list_url)
        dom = pq(rep.content)
        info_triples = []
        for table_element in dom('table.wikitable.typography-xl-optout'):
            table = pq(table_element)
            for tr_element in table('tr'):
                row = pq(tr_element)
                columns = row('td')
                if len(columns) > 0 and columns[0].text:
                    url = pq(columns[1])('a').attr('href')
                    if not url:
                        continue
                    sort_no = int(columns[0].text.strip())
                    name = pq(columns[1])('a').text().strip()
                    if sort_no in origin_sortno_set:
                        info_triples.append((sort_no, name, url))
                    self._build_en_name_mapping(sort_no, name)
        self._patch_en_name_mapping()
        with open('data/name.en.json', 'w') as fd:
            json_pretty_dump(self.en_name_map, fd)
        for info in info_triples:
            self.parse_ship_page(*info)
        return self.subtitles

    def parse_ship_page(self, sort_no, name, url):
        click.echo('Extracting {} - {} : {}'.format(sort_no, name, url))
        self.content = requests.get(self.host + url).content.decode('utf-8')
        page = pq(self.content)
        tables = page('table.wikitable.typography-xl-optout')
        self.ship = self.ship_service.get(sort_no=sort_no)
        self._build_kai_mapping()
        for i, table_element in enumerate(tables, 1):
            self.nth = i
            self.extract_dialogue_table(pq(table_element))
        self._merge_kai_quotes()
        with open('data/subtitlesEn.json', 'w') as fd:
            json_pretty_dump(self.subtitles, fd)

    def extract_dialogue_table(self, table):
        if table('th')[0].text is None:
            return
        header = table('th')[0].text.strip()
        if header == 'Time':
            ship_id = self._get_hourly_ship_id()
        else:
            ship_id = self._determine_target_ship()
        prev_symbol = ''
        prev_ship_id = -1
        prev_dialogue = ''
        for tr_element in table('tr'):
            row = pq(tr_element)
            columns = row('td')
            if len(columns) < 1:
                continue
            if len(columns) == 1 and prev_symbol:
                text = pq(columns[0]).text().strip()
                if re.search(r'shared with', text):
                    shares = [self._parameterize(x) for x in re.split(r'.*? shared with |,| and ', text) if x]
                    for share_symbol in shares:
                        # self._set_dialogue(prev_ship_id, share_symbol, prev_dialogue)
                        pass
            else:
                symbol = self._parameterize(pq(columns[0]).text())
                dialogue = pq(columns[2]).text().strip().replace('\n', ' ')
                if not dialogue:
                    continue
                matches = re.match('^(.*?)_?\((.*?)\)$', symbol)
                if matches:
                    symbol, kai_symbol = matches.groups()
                    if kai_symbol in self.kai_map:
                        kai_id = self.kai_map[kai_symbol]
                        self._set_dialogue(kai_id, symbol, dialogue)
                        prev_ship_id = kai_id
                    else:
                        self._set_dialogue(ship_id, symbol + '_' + kai_symbol, dialogue)
                elif symbol in self.kai_map:
                    kai_id = self.kai_map[symbol]
                    symbol = prev_symbol
                    self._set_dialogue(kai_id, symbol, dialogue)
                    prev_ship_id = kai_id
                else:
                    self._set_dialogue(ship_id, symbol, dialogue)
                    prev_ship_id = ship_id
                prev_symbol = symbol
                prev_dialogue = dialogue

    def _determine_target_ship(self):
        """HACK - 处理千岁的特殊情况"""
        if self.nth == 2 and self.ship['id'] in [102]:
            return self.kai_map['carrier']
        return self.ship['id']

    def _get_hourly_ship_id(self):
        match = re.search('Hourly\s+?Notifications\s+?\((.*?)\)', self.content, re.IGNORECASE)
        if match:
            kai_symbol = self._parameterize(match.group(1))
            if kai_symbol in self.kai_map:
                return self.kai_map[kai_symbol]
            else:
                raise SubtitleServiceError('The name of ship in title "hourly notifications" not found: {}'.format(kai_symbol))
        return self.ship['id']

    def _build_en_name_mapping(self, sort_no, name):
        """Ship ID -> English Name"""
        ship = self.ship_service.get(sort_no=sort_no)
        # HACK: Hibiki Kai Ni
        if ship['id'] == 147:
            self.en_name_map[ship['id']] = 'verniy'
        else:
            self.en_name_map[ship['id']] = self._parameterize(name)

    def _build_kai_mapping(self):
        ship = self.ship
        base_name = self.en_name_map[ship['id']]
        self.kai_map = {}
        kai_id = ship['after_ship_id']
        while kai_id and kai_id not in self.kai_map.values():
            kai_name = self.en_name_map[kai_id]
            kai_ship = self.ships[kai_id]
            if re.match(base_name, kai_name):
                self.kai_map[re.sub(r'^' + base_name + r'_', '', kai_name)] = kai_id
            self.kai_map[kai_name] = kai_id
            kai_id = kai_ship['after_ship_id']

    def _patch_en_name_mapping(self):
        self.en_name_map[504] = 'kumano_kai_ni'
        self.en_name_map[509] = 'kumano_carrier_kai_ni'
        self.en_name_map[545] = self._parameterize('Saratoga Mk.II')
        self.en_name_map[550] = self._parameterize('Saratoga Mk.II Mod.2')

    def _parameterize(self, symbol):
        symbol = re.sub('\s+', ' ', re.sub(r'[≤≥]', '', symbol.replace('Play', '').strip())).replace(' ', '_').lower()
        return symbol

    def _set_dialogue(self, ship_id, symbol, dialogue):
        if symbol in EN_SYMBOL_TO_VOICE_ID:
            voice_id = EN_SYMBOL_TO_VOICE_ID[symbol]
            self.subtitles[ship_id][voice_id] = dialogue
        elif CONFIG['debug']:
            click.echo('Can not recognize this dialogue symbol: {}'.format(symbol))

    def _merge_kai_quotes(self):
        viewed_kai = set()
        kai_id = self.ship['after_ship_id']
        ship_id = self.ship['id']
        base_quotes = self.subtitles[ship_id]
        while kai_id and kai_id not in viewed_kai:
            kai_ship = self.ships[kai_id]
            kai_quotes_diff = self.subtitles[kai_id]
            self.subtitles[kai_id] = copy.deepcopy(base_quotes)
            if kai_quotes_diff:
                self.subtitles[kai_id].update(kai_quotes_diff)
            base_quotes = self.subtitles[kai_id]
            viewed_kai.add(kai_id)
            kai_id = kai_ship['after_ship_id']




class SubtitleServiceError(Exception):
    pass