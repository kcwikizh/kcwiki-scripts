# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from moebot import MwApi
import json
import re
import datetime
from shutil import copyfile
import requests
import schedule
import time
import argparse
import sys
import traceback
import copy
import yaml

config = yaml.load(open('../config.yaml', 'r'))


def extract(mw, title):
    rep = mw.pageid(title, convert_titles='zh-cn', redirect=True)
    if not rep['success']:
        print('Mediawiki API 发生错误')
        return ''
    pageid = list(rep['contents'].keys())[0]
    if int(pageid) == -1:
        print('页面【{}】不存在'.format(title))
        return ''
    rep = mw.content(pid=pageid)
    if not rep['success']:
        print('Mediawiki API 发生错误')
        return ''
    content = rep['contents'][pageid]['revisions'][0]['*']
    return content


def post_process(content, lang='zh'):
    content = re.sub(r'{{ruby-zh\|(.*?)\|(.*?)}}', r'\1(\2)', content)
    if lang == 'zh':
        pattern = re.compile(r'\{\{台词翻译表(?:.|\n)*?档名\s*?=(.*?)\s*?\n(?:.|\n)*?中文译文\s*?=([^\|\{\}]*?)(?:\|(?:.|\n)*?)?\}\}',
                             re.MULTILINE)
    elif lang == 'jp':
        pattern = re.compile(r'\{\{台词翻译表(?:.|\n)*?档名\s*?=(.*?)\s*?\n(?:.|\n)*?日文台词\s*?=([^\|\{\}]*?)(?:\|(?:.|\n)*?)?\}\}',
                             re.MULTILINE)
    results = re.findall(pattern, content)
    namemap = json.load(open('../data/namemap.json', 'r'))
    post_results = []
    for item in results:
        filename, dialogue = item
        if not filename or not dialogue or len(filename.split('-')) < 2:
            continue
        dialogue = re.sub(r'<br.*?>', '', dialogue)
        dialogue = re.sub(r'<(.*)>.*?<\/\1>', '', dialogue)
        dialogue = dialogue.replace('\n', '')
        no = filename.split('-')[0].strip()
        if filename.split('-')[1] in namemap:
            mp3 = namemap[filename.split('-')[1]]
        else:
            continue
        print('{}, {}.mp3, {}'.format(no, mp3, dialogue))
        post_results.append((no, mp3, dialogue))
    return post_results


def search_ship(ships, sortno):
    for ship in ships:
        if not ship:
            continue
        if ship['sort_no'] == sortno:
            return ship


def post_process_for_season(content, lang='zh'):
    content = re.sub(r'{{ruby-zh\|(.*?)\|(.*?)}}', r'\1(\2)', content)
    if lang == 'zh':
        pattern = re.compile(r'\{\{台词翻译表(?:.|\n)*?档名\s*?=(.*?)\s*?\n(?:.|\n)*?中文译文\s*?=([^\|\{\}]*?)(?:\|(?:.|\n)*?)?\}\}',
                             re.MULTILINE)
    elif lang == 'jp':
        pattern = re.compile(r'\{\{台词翻译表(?:.|\n)*?档名\s*?=(.*?)\s*?\n(?:.|\n)*?日文台词\s*?=([^\|\{\}]*?)(?:\|(?:.|\n)*?)?\}\}',
                             re.MULTILINE)
    results = re.findall(pattern, content)
    post_results = []
    for item in results:
        filename, dialogue = item
        if not filename or not dialogue or len(filename.split('-')) < 2:
            continue
        dialogue = re.sub(r'<br.*?>', '', dialogue).strip()
        dialogue = re.sub(r'<(.*)>.*?<\/\1>', '', dialogue)
        no = filename.split('-')[0]
        archive_name = filename.split('-')[1]
        with open('../data/namemap.json', 'r') as f:
            namemap = json.load(f)
            pattern = re.compile(r'({})'.format('|'.join(namemap.keys())))
            voice = re.findall(pattern, filename)
            if len(voice) < 1:
                print('季节性档名异常，档名：{}'.format(filename))
                voice_no = 2
            else:
                voice_no = namemap[voice[0]]
        post_results.append((no, dialogue, voice_no))
    return post_results


def handleSeason(mw, ships, subtitles, title, lang):
    content = extract(mw, title)
    results = post_process_for_season(content, lang)
    print(len(results))
    for sortno, dialogue, voice_no in results:
        ship = search_ship(ships, int(sortno))
        print(ship['id'], ship['name'], dialogue, voice_no)
        if ship['id'] not in subtitles:
            subtitles[ship['id']] = {}
        subtitles[ship['id']][voice_no] = dialogue
        loop_count = 0
        while int(ship['after_ship_id']) > 0 and loop_count < 10:
            loop_count += 1
            ship = ships[int(ship['after_ship_id'])]
            if ship['id'] not in subtitles:
                subtitles[ship['id']] = {}
            subtitles[ship['id']][voice_no] = dialogue
    return subtitles


def generate_subtitles(results, ships, ship, subtitles_map, subtitles_distinct):
    subtitles = {}
    for no, mp3, dialogue in results:
        if no.endswith('a'):
            continue
        if int(no) == int(ship['sort_no']):
            subtitles[mp3] = dialogue
    subtitles_map[int(ship['id'])] = subtitles
    subtitles_distinct[int(ship['id'])] = copy.copy(subtitles)
    if int(ship['after_ship_id']) <= 0:
        return
    shipKai = ships[int(ship['after_ship_id'])]
    subtitlesKai = subtitles.copy()
    subtitles_distinct[int(shipKai['id'])] = {}
    print('读取【{}】的翻译'.format(shipKai['name']))
    for no, mp3, dialogue in results:
        if no.endswith('a') and int(no[:-1]) == int(ship['sort_no'])\
                or not no.endswith('a') and int(no) == int(shipKai['sort_no']):
            subtitlesKai[mp3] = dialogue
            subtitles_distinct[int(shipKai['id'])][mp3] = dialogue
    subtitles_map[int(shipKai['id'])] = subtitlesKai
    while int(shipKai['after_ship_id']) > 0 and\
            not int(shipKai['after_ship_id']) in subtitles_map:
        shipKai = ships[int(shipKai['after_ship_id'])]
        subtitlesKai = subtitlesKai.copy()
        subtitles_distinct[int(shipKai['id'])] = {}
        print('读取【{}】的翻译'.format(shipKai['name']))
        for no, mp3, dialogue in results:
            if no.endswith('a'):
                continue
            if int(no) == int(shipKai['sort_no']):
                subtitlesKai[mp3] = dialogue
                subtitles_distinct[int(shipKai['id'])][mp3] = dialogue
        subtitles_map[int(shipKai['id'])] = subtitlesKai


def main():
    mw = MwApi('http://zh.kcwiki.moe/api.php')
    mw.login(config['account']['username'], config['account']['password'])
    subtitles_map_zh = {}
    subtitles_map_jp = {}
    subtitles_distinct = {'zh': {}, 'jp': {}}
    ships = json.load(open('../data/ship.json', 'r'))
    ships = ships[:480]
    missing = []
    ext_title_map = {
        'まるゆ': '丸输',
        '武蔵': '武藏',
        'Bismarck': '俾斯麦',
        'あきつ丸': '秋津丸'
    }
    for ship in ships:
        if not ship or ship['name'].find('改') >= 0\
                or int(ship['id']) in subtitles_map_zh\
                or ship['name'].find('zwei') >= 0\
                or ship['name'].find('drei') >= 0:
            continue
        title = ship['name'].replace('黒', '黑')\
            .replace('巻', '卷').replace('満', '满')\
            .replace('穂', '穗').replace('歳', '岁')\
            .replace('叡', '睿')
        if title in ext_title_map:
            title = ext_title_map[title]
        print('正在获取【{}】页面'.format(title))
        content = extract(mw, title)
        results = post_process(content, 'zh')
        if len(results) <= 0:
            print('缺少【{}】的语音翻译'.format(title))
            missing.append(title)
            continue
        generate_subtitles(results, ships, ship,
                           subtitles_map_zh, subtitles_distinct['zh'])
        results = post_process(content, 'jp')
        generate_subtitles(results, ships, ship,
                           subtitles_map_jp, subtitles_distinct['jp'])

    handleSeason(mw, ships, subtitles_map_zh, '季节性/2016年初夏季节', 'zh')
    handleSeason(mw, ships, subtitles_map_jp, '季节性/2016年初夏季节', 'jp')
    handleSeason(mw, ships, subtitles_map_zh, '季节性/2016年盛夏季节', 'zh')
    handleSeason(mw, ships, subtitles_map_jp, '季节性/2016年盛夏季节', 'jp')

    suffix = ''
    now = datetime.datetime.now().strftime('%Y%m%d%H') + suffix
    subtitles_map_zh['version'] = now
    subtitles_map_jp['version'] = now
    deployFilename = '{}.json'.format(now)
    json.dump(subtitles_map_zh, open('../data/subtitles.json', 'w'))
    json.dump(subtitles_map_jp, open('../data/subtitlesJP.json', 'w'))
    json.dump(subtitles_map_zh, open('../data/' + deployFilename, 'w'))
    json.dump(subtitles_distinct, open('../data/subtitles_distinct.json', 'w'))
    json.dump(missing, open('../data/missing.json', 'w'))
    return (deployFilename, 'subtitlesJP.json')


def test():
    mw = MwApi('http://zh.kcwiki.moe/api.php')
    mw.login(config['account']['username'], config['account']['password'])
    title = '伊19'
    results = extract(mw, title)
    results = post_process(results)
    if len(results) <= 0:
        print('缺少【{}】的语音翻译'.format(title))


def deploy():
    try:
        env = config['env']
        # deployDir = '/var/www/api.kcwiki.moe/storage/app/subtitles/'
        deployDir = config[env]['subtitle']
        deployFilename, deployJpFilename = main()
        if not deployFilename:
            return
        copyfile('../data/' + deployFilename, deployDir + 'zh-cn/' + deployFilename)
        copyfile('../data/' + deployJpFilename, deployDir + 'jp/' + deployFilename)
        copyfile('../data/subtitles_distinct.json', deployDir + 'subtitles_distinct.json')
        # TODO git commit
        metaFile = deployDir + 'meta.json'
        meta = json.load(open(metaFile, 'r'))
        meta['latest'] = deployFilename[:-5]
        json.dump(meta, open(metaFile, 'w'))
        # Purge cache in api.kcwiki.moe
        requests.get('http://api.kcwiki.moe/purge')
    except KeyboardInterrupt as e:
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()


def plan():
    schedule.every().day.at("05:00").do(deploy)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("test", choices=['main', 'test', 'deploy', 'plan'])
    args = parser.parse_args()
    if args.test == 'main':
        main()
    elif args.test == 'test':
        test()
    elif args.test == 'deploy':
        deploy()
    elif args.test == 'plan':
        plan()
