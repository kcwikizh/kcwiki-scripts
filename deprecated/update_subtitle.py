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
        post_results.append((no, dialogue))
    return post_results


def handleSeason(mw, ships, subtitles, title, no, lang):
    content = extract(mw, title)
    results = post_process_for_season(content, lang)
    print(len(results))
    for sortno, dialogue in results:
        ship = search_ship(ships, int(sortno))
        print(ship['id'], ship['name'], dialogue)
        if ship['id'] not in subtitles:
            subtitles[ship['id']] = {}
        subtitles[ship['id']][no] = dialogue
        loop_count = 0
        while int(ship['after_ship_id']) > 0 and loop_count < 10:
            loop_count += 1
            ship = ships[int(ship['after_ship_id'])]
            if ship['id'] not in subtitles:
                subtitles[ship['id']] = {}
            subtitles[ship['id']][no] = dialogue
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


def monkey_patch(subtitles_map_jp, subtitles_map_zh):
    # Change taihou's subtitle
    subtitles_map_zh[153][2] = '雨一直不停的话，会妨碍到舰载机的训练。好担心航空队的练度。嗯—'
    subtitles_map_zh[153][3] = '对了，想象成暴雨时出动的训练不就可以了。 好！舰载机全员，准备训…咦，人呢？咦…？'
    subtitles_map_jp[153][2] = '雨が続くと、艦載機の訓練に支障が出るわね。航空隊の練度が心配。んー'
    subtitles_map_jp[153][3] = 'そうか、荒天時運用の訓練と考えればいいのよね。 よし！艦載機の皆さん、訓練に…あれ、皆さん？あれ…？'
    subtitles_map_zh[156][2] = '雨一直不停的话，会妨碍到舰载机的训练。好担心航空队的练度。嗯—'
    subtitles_map_zh[156][3] = '对了，想象成暴雨时出动的训练不就可以了。 好！舰载机全员，准备训…咦，人呢？咦…？'
    subtitles_map_jp[156][2] = '雨が続くと、艦載機の訓練に支障が出るわね。航空隊の練度が心配。んー'
    subtitles_map_jp[156][3] = 'そうか、荒天時運用の訓練と考えればいいのよね。 よし！艦載機の皆さん、訓練に…あれ、皆さん？あれ…？'
    # Change yuutachi's subtitle
    subtitles_map_zh[45][2] = '嗯，下雨天虽然会变得懒懒的不想出门，但是，还是要出去了poi！po~i！'
    subtitles_map_jp[45][2] = 'んん、雨の日は出無精になってしまいがちだけど、でも、外に出かけるっぽい！ぽーい！'
    subtitles_map_zh[45][3] = '呜嗯~好舒服POI！o(≧v≦)o~~'
    subtitles_map_jp[45][3] = 'うぅ、うぅ～んっ、気持ちいいっぽーい！'
    subtitles_map_zh[245][2] = '嗯，下雨天虽然会变得懒懒的不想出门，但是，还是要出去了poi！po~i！'
    subtitles_map_jp[245][2] = 'んん、雨の日は出無精になってしまいがちだけど、でも、外に出かけるっぽい！ぽーい！'
    subtitles_map_zh[245][3] = '呜嗯~好舒服POI！o(≧v≦)o~~'
    subtitles_map_jp[245][3] = 'うぅ、うぅ～んっ、気持ちいいっぽーい！'
    subtitles_map_zh[144][2] = '嗯，下雨天虽然会变得懒懒的不想出门，但是，还是要出去了poi！po~i！'
    subtitles_map_jp[144][2] = 'んん、雨の日は出無精になってしまいがちだけど、でも、外に出かけるっぽい！ぽーい！'
    subtitles_map_zh[144][3] = '呜嗯~好舒服POI！o(≧v≦)o~~'
    subtitles_map_jp[144][3] = 'うぅ、うぅ～んっ、気持ちいいっぽーい！'
    # Change murasame's subtitle
    subtitles_map_zh[44][2] = '晴天娃娃…？那，村雨来做一个试试吧。看好，这里要这样子…做好了。'
    subtitles_map_jp[44][2] = 'てるてる坊主…？じゃぁ、村雨が作ってみますね。ほら、ここをこうして…できました。'
    subtitles_map_zh[244][2] = '晴天娃娃…？那，村雨来做一个试试吧。看好，这里要这样子…做好了。'
    subtitles_map_jp[244][2] = 'てるてる坊主…？じゃぁ、村雨が作ってみますね。ほら、ここをこうして…できました。'
    # Patch hibiki's subtitle
    subtitles_map_zh[35][2] = '电酱的晴天娃娃，真不错，好可爱呢。晓的那个，什么玩意儿，怪兽嘛？ '
    subtitles_map_jp[35][2] = '電のてるてる坊主、いいな、可愛い。暁のそれは、何だい、怪獣？ '
    subtitles_map_zh[235][2] = '电酱的晴天娃娃，真不错，好可爱呢。晓的那个，什么玩意儿，怪兽嘛？ '
    subtitles_map_jp[235][2] = '電のてるてる坊主、いいな、可愛い。暁のそれは、何だい、怪獣？ '
    subtitles_map_zh[147][2] = '电酱的晴天娃娃，真不错，好可爱呢。晓的那个，什么玩意儿，怪兽嘛？ '
    subtitles_map_jp[147][2] = '電のてるてる坊主、いいな、可愛い。暁のそれは、何だい、怪獣？ '
    subtitles_map_zh[147][3] = '司令官的手……好温暖。在苏联的时候，这样的一双手绝对是我最珍贵的宝物。 '
    subtitles_map_jp[147][3] = '司令官の手は、温かいな。…いや、その…ロシアでは、重宝される手だ '



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

    # 情人节
    # subtitles_map = handleSeason(mw, ships, subtitles_map, '季节性/2016年白色情人节', 2)
    # 春季语音
    # handleSeason(mw, ships, subtitles_map_zh, '季节性/2016年春至', 2, 'zh')
    # handleSeason(mw, ships, subtitles_map_jp, '季节性/2016年春至', 2, 'jp')
    handleSeason(mw, ships, subtitles_map_zh, '季节性/2016年梅雨季节', 2, 'zh')
    handleSeason(mw, ships, subtitles_map_jp, '季节性/2016年梅雨季节', 2, 'jp')
    handleSeason(mw, ships, subtitles_map_zh, '季节性/2016年初夏季节', 2, 'zh')
    handleSeason(mw, ships, subtitles_map_jp, '季节性/2016年初夏季节', 2, 'jp')

    # Monkey Patch for spring rainy event (ry
    monkey_patch(subtitles_map_jp, subtitles_map_zh)

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
        # copyfile('subtitles_distinct.json', deployDir + '../subtitles_distinct.json')
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
