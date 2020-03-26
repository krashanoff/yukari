import datetime as dt
import json

class Media:
    def __init__(self,
                 idAni = int(),
                 idMal = int(),
                 title = dict(),
                 siteUrl = str()):
        self.idAni = idAni
        self.idMal = idMal
        self.title = title
        self.siteUrl = siteUrl

    # TODO: Pretty-print
    def __str__(self):
        return str(self.title)

    @staticmethod
    def from_json(obj = dict()):
        idAni = obj.pop('id')
        return Media(idAni, **obj)