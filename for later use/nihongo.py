#!/usr/bin/python

'''

The nihongo module provides basic support for simple mechanical language
transliteration between English and Japanese words, using Jim Breen's
JMdict database file.

SYNOPSIS

    >> from nihongo import *
    >> db = JmDict('JMdict_e')

    >> import romaji
    >> term = romaji.kana('konnichiha')
    >> entries = db.find(term)

AUTHOR

    Ed Halley (ed@halley.cc) 10 December 2007

'''

__all__ = [ 'JmDict', 'JmDictEntry', 'JmDictEntrySense',
            'is_hiragana', 'is_katakana', 'is_kanji',
            'Nihongo' ]

#----------------------------------------------------------------------------

import os
import re
import sys
import romaji
import codecs
import cPickle as pickle
from xml.sax import handler, make_parser

def _file_newer(a, b):
    '''Returns True if the first named file is newer than the second.'''
    if not os.path.exists(a): return False
    if not os.path.exists(b): return False
    return os.path.getmtime(a) > os.path.getmtime(b)

def _dict_replace(s, d):
    """Replace substrings of a string using a dictionary."""
    i = d.items()
    i.sort(lambda x,y: len(y[1])-len(x[1]))
    for key, value in i:
        s = s.replace(key, value)
    return s

def _dict_unreplace(s, d):
    """Replace substrings of a string using a reverse dictionary."""
    i = d.items()
    i.sort(lambda x,y: len(y[1])-len(x[1]))
    for key, value in i:
        s = s.replace(value, key)
    return s

#----------------------------------------------------------------------------

def load_jmdict(filename):
    return JmDict.load(filename)

class JmDict (object):

    def __init__(self, filename=None):
        self._seq = { }
        self._keb0 = { }
        self._reb0 = { }
        if filename:
            db = self.__class__.load(filename)
            if db:
                self._seq = db._seq
                self._keb0 = db._keb0
                self._reb0 = db._reb0

    @classmethod
    def load(cls, filename):
        places = [ os.path.dirname(filename), '.',
                   os.path.dirname(__file__) ]
        basename = os.path.basename(filename)
        for place in places:
            filename = os.path.join(place, basename)
            if os.path.exists(filename):
                break
        if not os.path.exists(filename):
            print 'Dictionary file %s not found' % filename
            return None

        db = None
        alternate = filename + '.pickle'
        if _file_newer(alternate, filename):
            try:
                f = file(filename + '.pickle', 'rb')
                print 'Loading precompiled dictionary...'
                db = pickle.load(f)
                f.close()
            except:
                print sys.exc_info()[0]

        if not db:
            print 'Loading standard dictionary...'
            db = JmDict()
            handler = JmDictHandler(db)
            handler.scanEntities(filename)
            parser = make_parser()
            parser.setContentHandler(handler)
            parser.parse(filename)
            #
            f = file(filename + '.pickle', 'wb')
            print 'Saving compiled dictionary...'
            pickle.dump(db, f)
            f.close()

        print 'Found', db.size(), 'entries.'
        return db

    def get(self, seq):
        if seq in self._seq:
            return self._seq[seq]
        return None

    def add(self, entry):
        '''Adds a dictionary entry and indexes it by kana and kanji heads.'''
        self._seq[entry.seq] = entry
        keb0s = set([ keb[0] for keb in entry.keb ])
        for keb0 in keb0s:
            if not keb0 in self._keb0: self._keb0[keb0] = [ ]
            self._keb0[keb0].append(entry)
        reb0s = set([ reb[0] for reb in entry.reb ])
        for reb0 in reb0s:
            if not reb0 in self._reb0: self._reb0[reb0] = [ ]
            self._reb0[reb0].append(entry)
        return len(self._seq)

    def size(self):
        '''Returns the number of dictionary entries known.'''
        return len(self._seq)

    def find(self, word, roma=True, kana=True, kanji=True):
        '''Searches for entries matching given word (in kana or kanji).'''
        if not word: return None
        found = [ ]
        if roma and is_other(word[0]):
            word = romaji.kana(word)
            kana = True
        if kanji and word[0] in self._keb0:
            found.extend( [ e for e in self._keb0[word[0]] if e == word ] )
        if kana and word[0] in self._reb0:
            found.extend( [ e for e in self._reb0[word[0]] if e == word ] )
        # search by english words in meanings is not yet supported
        return found
 
    def roma(self, word):
        found = self.find(word)
        if found:
            word = found[0].reb[0]
        return romaji.roma(word)

    def kana(self, word):
        found = self.find(word)
        if found:
            word = found[0].reb[0]
        return word

class JmDictEntry (object):

    def __init__(self):
        self.seq = None
        self.keb = []
        self.reb = []
        self.senses = []

    def __repr__(self):
        text = 'JMDictEntry(%d, %s\n' % (self.seq, self.keb)
        text += ' %s,\n' % self.reb
        text += ' %r)' % self.senses
        return text

    def __str__(self):
        text = ''
        #text += '#%d: ' % self.seq
        text += ','.join(self.keb)
        text += ' [' + ', '.join(self.reb) + ']'
        if len(self.senses) == 1:
            text += ' %s' % self.senses[0]
        else:
            for i in range(len(self.senses)):
                if i > 0: text += ';'
                text += ' (%d) %s' % (i+1, self.senses[i])
        return text

    def html(self): 
        return self.__str__()

    def __eq__(self, other):
        if self is other:
            return True
        for keb in self.keb:
            if keb == other:
                return True
        for reb in self.reb:
            if reb == other:
                return True
        return False

    def is_pos(self, pos):
        pos = pos.lower()
        pos = pos.replace('_', '-')
        for i in range(len(self.senses)):
            if pos in self.senses[i].pos:
                return True
        return False

    def is_uk(self):
        for i in range(len(self.senses)):
            if self.senses[i].uk:
                return True
        return False

class JmDictEntrySense (object):

    def __init__(self):
        self.uk = False
        self.pos = []
        self.misc = []
        self.gloss = []

    def __repr__(self):
        text = ''
        text += 'uk=%s ' % self.uk
        text += 'pos=%s ' % self.pos
        text += 'gloss=' + '/'.join(self.gloss)
        return text

    def __str__(self):
        text = ''
        if self.uk: text += '(uk) '
        if self.pos: text += '(' + ', '.join(self.pos) + ') '
        text += '; '.join(self.gloss)
        return text

    def html(self): 
        return self.__str__()

class JmDictHandler (handler.ContentHandler):

    def __init__(self, db):
        self._entities = {}
        self._entry = None
        self._sense = None
        self._text = ""
        self._db = db

    def scanEntities(self, filename):
        # assumes all entities are single-line
        # assumes no comments include <[doctype...]> bits
        # assumes no comments include <!entity...> bits
        f = codecs.open(filename, 'r', 'utf-8')
        doctype = 'JMdict'
        while True:
            line = f.readline()
            if line == '': break
            if ']>' in line: break
            m = re.search(r'<!DOCTYPE\s+(\S+)\s+\[', line)
            if m: doctype = m.group(1)
            if ('<%s>' % doctype) in line: break
            m = re.search(r'<!ENTITY\s+(\S+)\s+"(.*?)"\s*>', line)
            if not m: continue
            self._entities["&%s;" % m.group(1)] = m.group(2)
        f.close()

    def startElement(self, name, attrs):
        if name == 'entry':
            self._entry = JmDictEntry()
        if name == 'sense':
            self._sense = JmDictEntrySense()
        if name in [ 'ent_seq', 'keb', 'reb', 'gloss', 'pos', 'misc', ]:
            self._text = ""

    def characters(self, content):
        self._text = self._text + content

    def worthy(self, entry):
        return True

    def endElement(self, name):
        if name == 'entry':
            count = self._db.add(self._entry)
            if 0 == (count % 10000):
                print "Now", count, "..."
        if name == 'sense':
            self._entry.senses.append(self._sense)
        if name == 'ent_seq':
            self._entry.seq = int(self._text)
        if name == 'keb':
            self._entry.keb.append(self._text)
        if name == 'reb':
            self._entry.reb.append(self._text)
        if name == 'pos':
            self._text = _dict_unreplace(self._text, self._entities)
            pos = self._text
            if pos[0] == '&' and pos[-1] == ';':
                pos = pos[1:-1]
            self._sense.pos.append(pos)
        if name == 'misc':
            self._text = _dict_unreplace(self._text, self._entities)
            if u'&uk;' in self._text:
                self._sense.uk = True
        if name == 'gloss':
            self._sense.gloss.append(self._text)

    def endDocument(self):
        pass

#----------------------------------------------------------------------------

def is_other(c):
    if ord(c) <= 0x303F: return True
    if is_kanji(c): return False
    if is_hiragana(c): return False
    if is_katakana(c): return False
    return True

def is_hiragana(c):
    c = ord(c)
    if 0x3040 <= c <= 0x309F: return True
    return False

def is_katakana(c):
    c = ord(c)
    if 0x30A0 <= c <= 0x30FF: return True
    if 0x31F0 <= c <= 0x31FF: return True
    return False

def is_kanji(c):
    # rather simplistic view of the world, ne?
    return ord(c) > 0x30FF

class Illumination (object):

    def __init__(self):
        self.furigana = []
        self.literal = []
        self.formic = []
        self.kanji = []
        self.dbix = []
        self.pos = []

    def add(self, literal, form=None, furigana='', kanji='', entry=None, pos=None):
        self.furigana.append(furigana)
        self.literal.append(literal)
        self.formic.append(form)
        self.kanji.append(kanji)
        if isinstance(entry, JmDictEntry): entry = entry.seq
        self.dbix.append(entry)
        self.pos.append(pos)

    def entries(self, db):
        r = []
        s = set([])
        for e in self.dbix:
            if not e: continue
            if e in s: continue
            r.append(db.get(e))
            s.add(e)
        return r

    def __str__(self):
        return self.text()

    def text(self, db=None):
        out = u''
        for i in range(len(self.literal)):
            out += self.literal[i]
            if self.furigana[i]: out += u'[%s]' % self.furigana[i]
            if db:
                definition = db.get(self.dbix[i])
                if self.formic[i]: out += u' {%s}'% self.formic[i]
                if self.dbix[i]: out += u' %s' % definition
        return out

    def html(self, furigana=True, literal=True, reference=True):
        html = ''
        html += '<table class="nihongo">\n'
        if furigana:
            html += ' <tr class="furigana">'
            for i in range(len(self.literal)):
                if self.furigana[i] and self.furigana[i] != self.literal[i]:
                    html += '<td nowrap=1>%s</td>' % self.furigana[i]
                else:
                    html += '<td></td>'
            html += ' </tr>\n'
        if literal:
            html += ' <tr class="literal">'
            for i in range(len(self.literal)):
                html += '<td nowrap=1>%s</td>' % self.literal[i]
            html += ' </tr>\n'
        if reference:
            html += ' <tr class="reference">'
            for i in range(len(self.literal)):
                if self.dbix[i]:
                    html += '<td nowrap=1 class="link">#%s</td>' % self.dbix[i]
                else:
                    html += '<td></td>'
            html += ' </tr>\n'
        html += '</table>\n'
        return html

class Nihongo (object):

    # Particles follow words, phrases, sentences.
    # Lots of other particles, and compound-particles made from these.
    PARTICLES = [ 'ha', 'ga', 'no', 'ni', 'de', 'mo', 'e',
                  'ka', 'yo', 'ne', 'wa', 'na', 'ze', 'to',
                  'kara', 'made', 'hodo', 'yori', 'dake',
                  'shika', 'nagara', 'node', 'noni' ]

    POSES = [ 'V5R', 'V5S', 'V5G', 'V5M', 'V5N', 'V5T', 'V5U',
              'V5B', 'V5K', 'V1', 'VS_S', 'ADJ' ]

    STEMS = { 'V1': 'ru', 'V5R': 'ru', 'V5S':'su', 'V5G':'gu',
              'V5M':'mu', 'V5N':'nu', 'V5T':'tsu', 'V5U':'u',
              'V5B':'bu', 'V5K': 'ku', 'VS_S':'suru', 'ADJ':'i' }

    FORMS = set([])

    # The adj-i forms.
    ADJ = [ ('i', 'non-past'),
            ('katta', 'past'),
            ('kunai', 'negative non-past'),
            ('kunakatta', 'negative past'),
            None ]

    # The vs-* forms (<noun> suru).
    VS_S = [ ('suru', 'shimasu', 'non-past'),
             ('shita', 'shimashita', 'past'),
             ('shite', 'shimashite', 'te-form'),
             None ]

    # The v1 verb forms (ichidan).
    # The '''form''' notation indicates a special form,
    # linguistically special but not programmatically.
    #
    V1 = [ ('ru', 'masu', 'non-past'),
           ('tta', 'mashita', 'past'),
           ('te', 'mashite', 'te-form'),
           ('chau', 'complete te-form'),
           ('chatta', 'past complete te-form'),
           ('teiru', 'mashiteiru', 'progressive'),
           ('tara', 'mashitara', 'conditional'),
           ('reba', 'masunaraba', '''maseba''', 'provisional'),
           ('''reru''', '''remasu''', 'potential'),
           ('rareru', 'raremasu', 'passive'),
           ('raseru', 'sasemasu', 'causitive'),
           ('rasu', 'sashimasu', 'direct causitive'),
           ('rasarareru', 'rasareru',
            'saseraremasu', 'sasaremasu', 'causative-passive'),
           ('rou', 'mashou', 'volitional'),
           ('ruyounishou', 'rukotonishou',
            'ruyounishimashou', 'rukotonishimashou', 'hortative'),
           ('rudarou', 'rudeshou', 'conjectural'),
           ('ruttari', 'mashitari', 'alternative'),
           ('re', 'nasai', 'imperative'),
           ('runonara', 'correlational'),
           ('rukoto', 'descriptive'), 
           # V1 +-
           ('nai', '''nu''', '''zuni''', 'masen', 'negative non-past'),
           ('nakatta', 'masendeshita', 'negative past'),
           ('nakute', 'naide', 'masende', 'negative te-form'),
           ('nakuteiru', 'masendeiru', 'negative progressive'),
           ('nakattara', 'masendeshitara', 'negative conditional'),
           ('nakereba', 'masennaraba', 'negative provisional'),
           ('''renai''', '''remasen''', 'negative potential'),
           ('rarenai', 'raremasen', 'negative passive'),
           ('sasenai', 'sasanai',
            'sasemasen', 'sashimasen', 'negative causative'),
           ('saserarenai', 'sasarenai',
            'saseraremasen', 'sasaremasen', 'negative causative-passive'),
           ('''mai''', 'masumai', 'negative volitional'),
           ('naiyounishou', 'naikotonishou',
            'naiyounishimashou', 'naikotonishimashou',
            'negative hortative'),
           ('naiderou', 'ranaideshou', 'negative conjectural'),
           ('nakattari', 'masendeshitari', 'negative alternative'),
           ('runa', 'nasaruna', 'negative imperative'),
           [ 'ra', 'ri', 'ru', 're', 'ro' ] ]

    # The v5r form is the basis for all godan (v5_) forms.
    V5R = [ ('runonara', 'correlational'),
            ('ru', 'rimasu', 'non-past'),
            ('tta', 'rimashita', 'past'),
            ('tte', 'rimashite', 'te-form'),
            ('cchau', 'complete te-form'),
            ('cchatta', 'past complete te-form'),
            ('tteiru', 'rimashiteiru', 'progressive'),
            ('ttara', 'rimashitara', 'conditional'),
            ('reba', 'rimasunaraba', '''rimaseba''', 'provisional'),
            ('reru', 'remasu', 'potential'),
            ('rukoto', 'descriptive'),
            ('rareru', 'raremasu', 'passive'),
            ('raseru', 'rasemasu', 'causitive'),
            ('rasu', 'rashimasu', 'direct causitive'),
            ('raserareru', 'rasareru',
             'raseraremasu', 'rasaremasu', 'causative-passive'),
            ('rou', 'rimashou', 'volitional'),
            ('ruyounishou', 'rukotonishou',
             'ruyounishimashou', 'rukotonishimashou', 'hortative'),
            ('rudarou', 'rudeshou', 'conjectural'),
            ('ruttari', 'rimashitari', 'alternative'),
            ('re', 'rinasai', 'imperative'),
            # V5 +-
            ('ranai', '''ranu''', '''razuni''',
             'rimasen', 'negative non-past'),
            ('ranakatta', 'rimasendeshita', 'negative past'),
            ('ranakute', 'ranaide', 'rimasende', 'negative te-form'),
            ('ranakuteiru', 'rimasendeiru', 'negative progressive'),
            ('ranakattara', 'rimasendeshitara', 'negative conditional'),
            ('renakereba', 'rimasennaraba', 'negative provisional'),
            ('renai', 'remasen', 'negative potential'),
            ('rarenai', 'raremasen', 'negative passive'),
            ('rasenai', 'rasemasen', 'negative causitive'),
            ('raserarenai', 'rasarenai',
             'raseraremasen', 'rasaremasen', 'negative causative-passive'),
            ('''rumai''', 'rimasumai', 'negative volitional'),
            ('ranaiyounishou', 'ranaikotonishou',
             'ranaiyounishimashou', 'ranaikotonishimashou',
             'negative hortative'),
            ('ranaidarou', 'ranaideshou', 'negative conjectural'),
            ('ranakattari', 'rimasendeshitari', 'negative alternative'),
            ('runa', 'rinasaruna', 'negative imperative'),
            [ 'ra', 'ri', 'ru', 're', 'ro' ] ]

    # Other v5_ varieties differ from v5r in te-form and past only.
    # We derive the rest automatically in setup.
    V5S = [ ('shite', 'shimashite', 'te-form'),
            ('shita', 'shimashita', 'past'),
            ('shichau', 'complete te-form'),
            ('shichatta', 'past complete te-form'),
            ('shiteiru', 'shimashiteiru', 'progressive'),
            ('shittara', 'shimashitara', 'past'),
            [ 'sa', 'shi', 'su', 'se', 'so' ] ]
    V5K = [ ('ite', 'kimashite', 'te-form'),
            ('ita', 'kimashita', 'past'),
            ('ichau', 'complete te-form'),
            ('ichatta', 'past complete te-form'),
            ('iteiru', 'kimashiteiru', 'progressive'),
            ('itara', 'kimashitara', 'past'),
            [ 'ka', 'ki', 'ku', 'ke', 'ko' ] ]
    V5G = [ ('ide', 'gimashite', 'te-form'),
            ('ida', 'gimashita', 'past'),
            ('ijau', 'complete te-form'),
            ('ijatta', 'past complete te-form'),
            ('ideiru', 'gimashiteiru', 'progressive'),
            ('idara', 'gimashitara', 'past'),
            [ 'ga', 'gi', 'gu', 'ge', 'go' ] ]
    V5B = [ ('nde', 'bimashite', 'te-form'),
            ('nda', 'bimashita', 'past'),
            ('njau', 'complete te-form'),
            ('njatta', 'past complete te-form'),
            ('ndeiru', 'bimashiteiru', 'progressive'),
            ('ndara', 'bimashitara', 'past'),
            [ 'ba', 'bi', 'bu', 'be', 'bo' ] ]
    V5M = [ ('nde', 'mimashite', 'te-form'),
            ('nda', 'mimashita', 'past'),
            ('njau', 'complete te-form'),
            ('njatta', 'past complete te-form'),
            ('ndeiru', 'mimashiteiru', 'progressive'),
            ('ndara', 'mimashitara', 'past'),
            [ 'ma', 'mi', 'mu', 'me', 'mo' ] ]
    V5N = [ ('nde', 'nimashite', 'te-form'),
            ('nda', 'nimashita', 'past'),
            ('njau', 'complete te-form'),
            ('njatta', 'past complete te-form'),
            ('ndeiru', 'nimashiteiru', 'progressive'),
            ('ndara', 'nimashitara', 'past'),
            [ 'na', 'ni', 'nu', 'ne', 'no' ] ]
    V5T = [ [ 'ta', 'chi', 'tsu', 'te', 'to' ] ]
    V5U = [ [ 'wa', 'i', 'u', 'e', 'o' ] ]
    __SETUP = False

    def __init__(self, db=None):
        self._setup()
        if db is None:
            db = load_jmdict('JMdict_e')
        self.db = db
        if not self.db:
            raise Error, 'could not load dictionary'

    def _setup(self):
        if Nihongo.__SETUP: return
        Nihongo.__SETUP = True
        for pos in Nihongo.POSES:
            old = getattr(Nihongo, pos)
            gyou = old.pop()
            new = { }
            if pos.startswith('V5') and pos != 'V5R':
                new = Nihongo.V5R.copy() # assumes V5R is already done
                for v in range(5):
                    r = [ 'ra', 'ri', 'ru', 're', 'ro' ][v]
                    x = gyou[v]
                    for form in new:
                        new[form] = [ re.sub('^'+r, x, flect)
                                      for flect in new[form] ]
            for form in old:
		Nihongo.FORMS.add(form[-1])
                new[form[-1]] = form[:-1]
            setattr(Nihongo, pos, new)

    def leader(self, corpus):
        '''Return the first part of a phrase that is similar in writing.'''
        if not corpus:
            return ''
        token = corpus[0]
        corpus = corpus[1:]
        if is_other(token):
            while corpus != '' and is_other(corpus[0]):
                        token += corpus[0]
                        corpus = corpus[1:]
        elif is_hiragana(token):
            while corpus != '' and is_hiragana(corpus[0]):
                        token += corpus[0]
                        corpus = corpus[1:]
        elif is_katakana(token):
            while corpus != '' and is_katakana(corpus[0]):
                        token += corpus[0]
                        corpus = corpus[1:]
        elif is_kanji(token):
            while corpus != '' and (is_kanji(corpus[0]) or is_hiragana(corpus[0])):
                        token += corpus[0]
                        corpus = corpus[1:]
        return token

    def divide(self, word):
        '''Separate all trailing hiragana from a word or phrase.'''
        if not word:
            return (word, '')
        inflect = ''
        while is_hiragana(word[-1]):
            inflect = word[-1] + inflect
            word = word[:-1]
        return (word, inflect)

    def deinflect(self, corpus, explain=False):
        '''Attempt to find the plain form of an inflected word or phrase.'''
        variants = [ ]
        for pos in Nihongo.STEMS:
            forms = getattr(Nihongo, pos)
            stem = ''
            if not hasattr(Nihongo, pos):
                print 'no Nihongo attrib for pos %s' %s
                continue
            stem = romaji.kana(Nihongo.STEMS[pos])
            for form in forms:
                for variant in forms[form]:
                    kana = romaji.kana(variant)
                    if corpus.endswith(kana):
                        candidate = (pos, variant, len(kana), kana, stem, form)
                        variants.append( candidate )
        if not variants:
            if explain: return (corpus, None)
            return corpus
        variants.sort(lambda x,y: y[2]-x[2])
        while variants:
            winner = variants.pop()
            word = corpus[:-winner[2]] + winner[4]
            found = self.db.find(word)
            if found and found[0].is_pos(winner[0]):
                if explain: return (word, winner[-1])
                return word
        if explain: return (corpus, None)
        return corpus

    def common(self, a, b):
        '''Determine the common beginning and both endings of two phrases.'''
        c = ''
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]: break
            c += a[i]
        return (c, a[i:], b[i:])

    def erode(self, corpus):
        '''Return the largest beginning part of a phrase found as one word.'''
        if not corpus:
            return (None,None,None)
        found = None
        kana = None
        explain = None
        while corpus:
            found = self.db.find(corpus)
            plain = corpus
            if found: break
            (plain, explain) = self.deinflect(corpus, explain=True)
            found = self.db.find(plain)
            if found: break
            corpus = corpus[:-1]
        if found:
            found = found[0]
            kana = found.reb[0]
            if plain != corpus:
                (common, first, second) = self.common(corpus, plain)
                kana = kana[:-len(second)] + first
        return (found, explain, corpus, kana)

    def illuminate(self, corpus):
        '''Construct an illumination study of a phrase.'''
        ill = Illumination()
        illuminated = ''
        while corpus != '':
            lead = self.leader(corpus)
            if is_other(lead[0]):
                ill.add(lead)
            elif is_katakana(lead[0]) or is_hiragana(lead[0]):
                ill.add(lead)
            else:
                (entry, form, kanjiflect, kanaflect) = self.erode(lead)
                if entry:
                    ill.add(kanjiflect, form=form, kanji=kanjiflect,
                            furigana=kanaflect, entry=entry)
                    lead = kanjiflect
                else:
                    ill.add(lead, furigana=lead)
            corpus = corpus[len(lead):]
        return ill

    def translate(self, corpus):
        '''Simplify an illumination into word and phrase fragments.'''
        ill = self.illuminate(corpus)
        return ill.text(db=self.db)

#----------------------------------------------------------------------------

if __name__ == '__main__':

    try:
        import psyco
        psyco.full()
    except:
        print '(no psyco acceleration available)'
        pass
    
    import os
    sys.stdout = codecs.lookup('utf-8')[-1](sys.stdout)

    # load the dictionary
    db = JmDict('JMdict_e')

    # self-test: look up a common word
    if False:
        term = romaji.kana('konnichiha')
        entries = db.find(term)
        print term, '=>'
        for e in entries:
            print u' %s' % e
        for k in e.keb: print u' kanji: %s' % k
        for r in e.reb: print u'  kana: %s' % r
        if e.is_uk(): print 'usually kana'
        print

    # prepare for dictionary work
    corpus = []
    source = 'corpus.txt'
    xl = Nihongo(db)

    # self-test: de-inflect some simple words via dictionary
    if False:
        for pair in [ ('wakaru','ru','rimasen'),
                      ('sokusuru','suru','shite'),
                      ('isogashii','i','kunakatta') ]:
            word = romaji.kana(pair[0])
            print u'Trying to deinflect %s:' % word
            word = db.find(word)[0]
            print u'%s' % word
            word = word.keb[0]
            inflected = word[:-len(romaji.kana(pair[1]))] + romaji.kana(pair[2])
            plain = xl.deinflect(inflected)
            print 'xl.deinflect("%s") -> %s' % (inflected, plain)
            print

    # do what the user requests
    args = sys.argv
    args.pop(0)
    while args:
        arg = args.pop(0)

        if arg == '--corpus' and args:
            source = args.pop(0)

            try:
                f = codecs.open(source, 'r', 'utf-8')
                while True:
                    line = f.readline()
                    if not line: break
                    corpus.append(line.strip())
                f.close()
		f = None
            except Exception, e:
                print e
                print 'Could not open "%s" file to read.' % source
                corpus = u'\u5f7c\u306e\u4f1d\u8a18\u306f' # kare no denki ha
                corpus += u'\u5168\u304f\u306e' # mattaku no
                corpus += u'\u4e8b\u5b9f\u306b' # jijitsu ni
                corpus += u'\u5373\u3057\u3066' # soku shite (soku suru -> te-form)
                corpus += u'\u66f8\u304b\u308c\u305f\u3082\u306e' # sho kareta mono
                corpus += u'\u3060\u3002' # da .
                corpus += u'His biography is quite true to life.'
                corpus = [ corpus ]

    # output some html into a test file
    if False:
        f = codecs.open('test.html', 'w', 'utf-8')
        f.write('<html><head>\n')
        f.write('<meta http-equiv = "Content-Type" ' +
                'content = "text/html; charset=utf-8">\n')
        f.write('''<style type="text/css">
                table.nihongo { border=none }
                tr.furigana { font-size: 80%; text-align: center }
                tr.literal { font-size: 120%; text-align: center }
                tr.reference { font-size: 40%; color: #666666; text-align: center }
                td.link { border-top: 1px solid #888888 }
                </style>\n''')
        f.write('</head>\n<body>\n')

    # illuminate the text
    # (make a markup-friendly object breaking down each word)
    #
    print romaji.kana('genki')
    for sentence in corpus:
        print u'%s' % sentence

        ill = None
        if True:
            ill = xl.illuminate(sentence)
            print
            print ill.text()
            print

        # format the illumination into html
        if f and ill:
            f.write('<p>\n')
            f.write(ill.html())
            f.write('</p>\n')
            for entry in ill.entries(db):
                f.write(entry.html())
                f.write('\n<br>\n')
            f.write('<hr>')

    # wrap up
    if f:
        f.write('</body></html>')
        f.close()
        try:
            os.startfile('test.html')
        except:
            pass
