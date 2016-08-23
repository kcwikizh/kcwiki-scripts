import requests


class KcwikiApi(object):
    base = 'http://api.kcwiki.moe'

    @classmethod
    def ships(cls):
        rep = requests.get('{}/ships'.format(cls.base))
        return rep.json()
