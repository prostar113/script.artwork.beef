import xbmc

from lib.libs import mediatypes
from lib.libs.pykodi import json, UTF8JSONDecoder
from lib.libs.utils import SortedDisplay
from lib.providers.base import AbstractProvider, AbstractImageProvider, cache

api_key = '***REMOVED***'

# url param i=MB track/album/artist ID
artmap = {'mbtrack': {'datakey':'track', 'artmap': {'strTrackThumb': 'thumb'},
        'url': 'http://www.theaudiodb.com/api/v1/json/{0}/track-mb.php'.format(api_key)},
    'mbgroup': {'datakey':'album', 'artmap': {'strAlbumThumb': 'thumb', 'strAlbumCDart': 'discart',
            'strAlbumThumbBack': 'back', 'strAlbumSpine': 'spine'},
        'url': 'http://www.theaudiodb.com/api/v1/json/{0}/album-mb.php'.format(api_key)},
    'mbartist': {'datakey':'artists', 'artmap': {'strArtistThumb': 'thumb', 'strArtistLogo': 'clearlogo',
            'strArtistBanner': 'banner', 'strArtistFanart': 'fanart', 'strArtistFanart2': 'fanart',
            'strArtistFanart3': 'fanart', 'strArtistClearart': 'clearart', 'strArtistWideThumb': 'landscape'},
        'url': 'http://www.theaudiodb.com/api/v1/json/{0}/artist-mb.php'.format(api_key)}
}
provtypes = set(x for data in artmap.values() for x in data['artmap'].values())

def provides(types):
    return bool(set(types) & provtypes)

class TheAudioDBAbstractProvider(AbstractImageProvider):
    name = SortedDisplay('theaudiodb.com', 'TheAudioDB.com')
    contenttype = 'application/json'

    def get_data(self, url, params):
        result = cache.cacheFunction(self._get_data, url, params)
        return result if result != 'Empty' else None

    def _get_data(self, url, params):
        self.log('uncached', xbmc.LOGINFO)
        response = self.doget(url, params=params)
        return 'Empty' if response is None else json.loads(response.text, cls=UTF8JSONDecoder)


    def _build_image(self, url, size, title=None):
        result = {'provider': self.name, 'url': url, 'preview': url + '/preview',
            'size': size, 'language': None, 'rating': SortedDisplay(5.1 if title == 'track' else 5.0, '')}
        if title:
            result['title'] = title
        return result

class TheAudioDBMusicVideoProvider(TheAudioDBAbstractProvider):
    mediatype = mediatypes.MUSICVIDEO

    def get_images(self, uniqueids, types=None):
        if types is not None and not provides(types) or not ('mbtrack' in uniqueids or
                'mbgroup' in uniqueids or 'mbartist' in uniqueids):
            return {}

        images = {}
        for idsource, artdata in artmap.iteritems():
            if idsource not in uniqueids or types is not None and not \
                    any(x in types for x in artdata['artmap'].itervalues()):
                continue
            data = self.get_data(artdata['url'], {'i': uniqueids[idsource]})
            if not data or not data.get(artdata['datakey']):
                continue
            data = data[artdata['datakey']][0]
            for originaltype, finaltype in artdata['artmap'].iteritems():
                if (originaltype in ('strAlbumThumbBack', 'strAlbumSpine')):
                    continue
                if originaltype == 'strArtistThumb':
                    finaltype = 'artistthumb'
                elif originaltype in ('strTrackThumb', 'strAlbumThumb'):
                    finaltype = 'poster'
                if data.get(originaltype):
                    _insertart(images, finaltype, self._build_image(data[originaltype],
                        _get_imagesize(originaltype), artdata['datakey']))

        return images

class TheAudioDBAbstractMusicProvider(TheAudioDBAbstractProvider):
    def _inner_get_images(self, uniqueids, idsource, types):
        artdata = artmap[idsource]
        if types and not any(x in types for x in artdata['artmap'].itervalues()):
            return {}

        images = {}
        data = self.get_data(artdata['url'], {'i': uniqueids[idsource]})
        if not data or not data.get(artdata['datakey']):
            return {}
        data = data[artdata['datakey']][0]
        for originaltype, finaltype in artdata['artmap'].iteritems():
            if data.get(originaltype):
                _insertart(images, finaltype, self._build_image(data[originaltype],
                    _get_imagesize(originaltype), artdata['datakey']))

        return images

class TheAudioDBAlbumProvider(TheAudioDBAbstractMusicProvider):
    mediatype = mediatypes.ALBUM
    def get_images(self, uniqueids, types=None):
        return self._inner_get_images(uniqueids, 'mbgroup', types)

class TheAudioDBArtistProvider(TheAudioDBAbstractMusicProvider):
    mediatype = mediatypes.ARTIST
    def get_images(self, uniqueids, types=None):
        return self._inner_get_images(uniqueids, 'mbartist', types)

class TheAudioDBSongProvider(TheAudioDBAbstractMusicProvider):
    mediatype = mediatypes.SONG
    def get_images(self, uniqueids, types=None):
        return self._inner_get_images(uniqueids, 'mbtrack', types)

def _get_imagesize(arttype):
    if arttype in ('strTrackThumb', 'strAlbumThumb', 'strArtistThumb', 'strAlbumThumbBack'):
        return SortedDisplay(500, '500-800')
    if arttype in ('strAlbumCDart',):
        return SortedDisplay(500, '500 or 1000')
    if arttype in ('strArtistLogo',):
        return SortedDisplay(400, '400x155 or 800x310')
    if arttype in ('strArtistBanner',):
        return SortedDisplay(1000, '1000x185')
    if arttype in ('strArtistClearart', 'strArtistWideThumb'):
        return SortedDisplay(1000, '1000x562')
    if arttype in ('strArtistFanart', 'strArtistFanart2', 'strArtistFanart3'):
        return SortedDisplay(1280, '1280x720 or 1920x1080')
    if arttype in ('strAlbumSpine',):
        return (SortedDisplay(700, '700x35'))
    return SortedDisplay(0, '')

def _insertart(images, arttype, image):
    if arttype not in images:
        images[arttype] = []
    images[arttype].append(image)

class TheAudioDBSearch(AbstractProvider):
    name = SortedDisplay('theaudiodb.com:search', 'TheAudioDB.com search')
    contenttype = 'application/json'

    # s=[artist], t=[track title]
    url_trackby_artistandtrack = 'http://www.theaudiodb.com/api/v1/json/{0}/searchtrack.php'.format(api_key)

    def get_data(self, url, params=None):
        result = cache.cacheFunction(self._get_data, url, params)
        return result if result != 'Empty' else None

    def _get_data(self, url, params=None):
        self.log('uncached', xbmc.LOGINFO)
        if params is None:
            params = {}
        response = self.doget(url, params=params)
        return 'Empty' if response is None else response.json()

    def search(self, query, mediatype):
        if mediatype != mediatypes.MUSICVIDEO:
            return []
        query = query.split(' - ', 1)
        if len(query) != 2:
            return []
        data = self.get_data(self.url_trackby_artistandtrack, {'s': query[0], 't': query[1]})
        if not data or not data.get('track'):
            return []

        return [{'label': item['strArtist'] + ' - ' + item['strTrack'], 'uniqueids':
            {'mbtrack': item['strMusicBrainzID'], 'mbartist': item['strMusicBrainzArtistID'],
            'mbgroup': item['strMusicBrainzAlbumID']}} for item in data['track']]
