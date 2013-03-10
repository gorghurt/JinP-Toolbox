#!/usr/bin/python
# -*- coding: utf-8 -*-

#to do:-bug bei mehrmaligem drücken von Ausführen: Listen werden mehrfach hinzugefügt(aber nicht space)(kein fehler) X
#       -suport für nicht utf-8 files...eventuell mit beutufull soup
#      -lizenzen des benutzten fremdcodes lesen
#		-kanjicount sortiert nicht zuende
#		-besseren sortieralgorithmus benutzen !!!!!!!!!!! (teilweise geschafft, pythons sort kann nun genutzt werden, aber wordcount und kanjicount sind sehr langsam)
#		-auskommentieren


# komandozeilen Argumente:
#--help, --h,-h,-H,--H,--Help dieser text
#--s leerzeichen
#--k Kanji zählen und ausgeben
#--w Wörter zählen und ausgeben
#"--o <datei>" Ausgabe Datei
#--f <datei>   Eingabe Datei
#--t <text>    Text(wenn keine Eingabe Datei)
#--f ist mächtiger als --t
# wenn weder --f noch --t vorhanden sind wird um eine Eingabe gebeten.
#ist keine Ausgabedatei (--o) angegeben, erfolgt die Ausgabe über die Konsole
import MeCab
import encodings
#from BeautifulSoup import UnicodeDammit
from bs4 import UnicodeDammit

#from django.utils.encoding import smart_str, smart_unicode 
import sys
import sip
sip.setapi('QString', 2) #qstrings sind nun automatisch unicode objekte
from PyQt4 import QtGui , QtCore#, QTextCodec
import codecs
chasen=MeCab.Tagger("-O chasen")
wakati=MeCab.Tagger("-O wakati")
#text=""

s=False
k=False
w=False
O=False
ignore_words=["ある", "bla"];
ignore_kanji=["a","b","c"]
#blacklist für mecab, dinge wie hilfsverben und partikel und satzzeichen sollen nicht dazu
Blacklist=['助詞-係助詞','助動詞','記号-一般','記号-句点','助詞-格助詞-連語'] #partikel,   '名詞-サ変接続'-nomen-??? kommt bei satzzeichen


class Window(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        #Menü:
        exit = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        offnen = QtGui.QAction("Datei öffnen".decode("utf-8"),  self)
        offnen.setShortcut("Ctrl+O")
        #openact=self.open()#funktion zuweisen(sonst würde im nächsten schritt)
        ##rückgabewert als typ genommen werden, was nicht klappt
        self.connect(offnen, QtCore.SIGNAL("triggered()"), lambda: self.open())

        speichern = QtGui.QAction("Datei speichern".decode("utf-8"),  self)
        speichern.setShortcut("Ctrl+S")
        #openact=self.open()#funktion zuweisen(sonst würde im nächsten schritt)
        ##rückgabewert als typ genommen werden, was nicht klappt
        self.connect(speichern, QtCore.SIGNAL("triggered()"), lambda: self.save())

        statusbar=self.statusBar()

      #  self.progressbar=QtGui.QProgressBar()
      #  self.progressbar.setMinimum(0)
      #  self.progressbar.setMaximum(1)
      #  statusbar.addWidget(self.progressbar)

        #offnen.triggered.connect(open())
        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(exit)
        file.addAction(offnen)
        file.addAction(speichern)

        #widgets:


        self.textedit= QtGui.QTextEdit()
        self.eingabet=QtGui.QLabel()
        self.eingabet.setMaximumHeight(24)
        self.eingabet.setText("Eingabe:")
        self.ausgabete=QtGui.QTextEdit()
        self.ausgabete.setReadOnly(True)
        self.ausgabet=QtGui.QLabel()
        self.ausgabet.setMaximumHeight(24)
        self.ausgabet.setText("Ausgabe:")
        #self.textedit.setCurrentCharFormat("utf8")
        self.space=QtGui.QCheckBox('space', self)
        #spacea=lambda: space()
        #self.spacebutton.clicked.connect(lambda: self.space())
        self.Wort=QtGui.QCheckBox("Wörter zählen".decode("utf-8"), self)
        self.Kanji=QtGui.QCheckBox("Kanji zählen".decode("utf-8"), self)
	self.OriginalText=QtGui.QCheckBox("Original Text".decode("utf-8"),self)
	self.ignoreWords_Box = QtGui.QCheckBox("Wörter in Wortlise ignorieren".decode("utf-8"), self)
 	self.ignoreKanji_Box = QtGui.QCheckBox("Kanji in Kanjilise ignorieren".decode("utf-8"), self)

        self.processbutton=QtGui.QPushButton("Ausführen".decode("utf-8"))
        self.processbutton.clicked.connect(lambda: self.process_button())

      	split=QtGui.QSplitter()
      	split.setOrientation(QtCore.Qt.Vertical)
#Layout
      	grid0=QtGui.QGridLayout()
      	grid1=QtGui.QGridLayout()
        #grid = QtGui.QHBoxLayout()
        grid0.setSpacing(10) #oberer teil
        grid1.setSpacing(10) #unterer teil

        grid0.addWidget(self.eingabet,0,0)
        grid0.addWidget(self.textedit,1,0,5,4)
        grid0.addWidget(self.space,6,0)
        grid0.addWidget(self.Wort,6,1)
        grid0.addWidget(self.Kanji,6,2)
	grid0.addWidget(self.OriginalText,6,3)
        grid0.addWidget(self.processbutton,7,3)
	grid0.addWidget(self.ignoreWords_Box,7,1)
        grid0.addWidget(self.ignoreKanji_Box,7,2)

        grid1.addWidget(self.ausgabet,8,0)
        grid1.addWidget(self.ausgabete,9,0,13,4)
        Widget=QtGui.QWidget()
        Widget.setLayout(grid0)
        #Widget1=QtGui.QWidget()
        #Widget1.setLayout(grid)
        Widget2=QtGui.QWidget()
        Widget2.setLayout(grid1)
        split.addWidget(Widget)
        #split.addWidget(Widget1)
        split.addWidget(Widget2)
        self.setCentralWidget(split)
        #Widget.setLayout(split)
        self.setWindowTitle('JinP-Toolbox')
        #self.resize(640, 480)
        self.center()

    def center(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
    def open(self):
        #to do: exception einfügen führ fehlerhaftes öffnen
        data=self.textedit.toPlainText() #notlösung um überschreiben mit altem file zu verhindern
        filename = QtGui.QFileDialog.getOpenFileNameAndFilter(self, 'Open File', '.',"(*);;utf8(*);;euc-jp(*);;shift-jis(*);;ISO-2022-JP(*)")   
	#filename = QtGui.QFileDialog.getSaveFileName(self, 'Datei oeffnen', '', "utf8;;euc-jp;;shift-jis")     
	#fname = open(smart_str(filename))
	fname = open(filename[0])#.decode("utf8"))
        #data = smart_str(fname.read())
	data= UnicodeDammit(fname.read(),[filename[1]])  #"euc-jp",
	print("encoding:"+data.original_encoding) 
	#print(data.unicode_markup)     
	self.textedit.setPlainText(data.unicode_markup)	
	#self.textedit.setPlainText(data)#.decode("utf-8"))
        fname.close()

    def save(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '.')
        #fname = open(smart_str(filename), 'w')
	fname = open(filename, 'w')
        #fname.write(smart_str(self.ausgabete.toPlainText()))
        fname.write(self.ausgabete.toPlainText())
	fname.close()

    def process_button(self):
    	#self.progressbar.setMaximum(0)
        eingabe=UnicodeDammit(self.textedit.toPlainText()).unicode_markup#toUtf8
        #print eingabe
        #print smart_str(eingabe)
        ##text=tools.process(smart_str(eingabe),self.space.checkState(),self.Kanji.checkState(),self.Wort.checkState())
	#eingabe=self.textedit.toPlainText()
	if self.ignoreWords_Box.checkState() and self.ignoreKanji_Box.checkState():
		text=tools.process(eingabe,self.space.checkState(),self.Kanji.checkState(),self.Wort.checkState(),self.OriginalText.checkState(),ignore_words,ignore_kanji)
	elif self.ignoreWords_Box.checkState():
		text=tools.process(eingabe,self.space.checkState(),self.Kanji.checkState(),self.Wort.checkState(),self.OriginalText.checkState(),ignore_words,[])
	elif self.ignoreKanji_Box.checkState(): 
		text=tools.process(eingabe,self.space.checkState(),self.Kanji.checkState(),self.Wort.checkState(),self.OriginalText.checkState(),[],ignore_kanji)
	else:
		text=tools.process(eingabe,self.space.checkState(),self.Kanji.checkState(),self.Wort.checkState(),self.OriginalText.checkState())
       	# print smart_str(text)
        #self.ausgabete.setPlainText(smart_str(text).decode("utf-8"))
        self.ausgabete.setPlainText(text)
        #self.progressbar.setMaximum(1)

class tools:
	def space(self,text):
		#print "space in progress"
		global wakati
		#print smart_str(text)
		#zeilen einzeln durchgehen, da mecab  scheinbar die Umbrüche entfernt
		zeilen=text.split("\n")
		ausgabe=""
		for i in zeilen :
			ausgabe=ausgabe+wakati.parse(unicode(i).encode("utf-8"))
		return UnicodeDammit(ausgabe).unicode_markup
	def kanjicount(self,text):
		#print "kanjicount in progress"
		#words=list(smart_unicode(text))
		words=list(text)		
		count=[]
		count.append([])
		count.append([])
		words2=words[:]
		for item in words2:
			if item not in count[0] and item not in self.ignore_kanji:
				count[0].append(UnicodeDammit(item).unicode_markup)
				count[1].append(words.count(item))

		count[1].insert(0,len(count[0])) #anzahl der vorkommenden Wörter
		count[0].insert(0,"--")
		count[0].insert(0,"++") #gesammtzahl der wￃﾶrter im text oben einfￃﾼgen
		count[1].insert(0,len(words2))
		return count

	def wordcount(self,text):
		#print "wordcount in progress"
		global chasen
		eingabe= chasen.parse(text.encode("utf-8")) #chasen durchlaufen lassen
		zeilen=eingabe.splitlines() #nach zeilen trennen
		zeilen.pop() #letzte zeile löschen(nicht benötigt ?)
		words=list() #listen anlegen
		count=[]
		count.append([])
		count.append([])
		#print("wordcount: chasen durch")
		#nach tabs trennen und 3. item(wörter) benutzen
		for item in zeilen :
			tabs=item.split("\t")
			if tabs[3] not in Blacklist:
				words.append(tabs[2])
		#print "wordcount tabs durch"
		words2=words[:]  #wort liste kopieren
		for item in words2:
			itemunicode=UnicodeDammit(item).unicode_markup
			if itemunicode not in count[0] and item not in self.ignore_words:
				#löschen ist zeitaufwändiger als mehrmals ignorieren
				#while item in words:  #wort aus liste entfernen
				#	words.remove(item)
			#else:
				count[0].append(itemunicode)
				count[1].append(words.count(item))
		
		count[1].insert(0,len(count[0])) #anzahl der vorkommenden Wörter
		count[0].insert(0,"--")
		count[1].insert(0,len(words2)) #gesammtzahl der wￃﾶrter im text oben einfￃﾼgen
		count[0].insert(0,"++")
		return count

	def sortcount(self,count1):#tut noch nicht
		counte=count1[:]
		for i in range(len(count1[1])-1,0,-1):
			#print "a",i
			for j in range (0,i):
				if i-j>0:
					#print "b"
					if counte[1][i-j]>counte[1][(i-j)-1]:
						#print "t"
						temp0=counte[0][i-j]
						counte[0][i-j]=counte[0][i-(j+1)]
						counte[0][i-(j+1)]=temp0
						temp1=counte[1][i-j]
						counte[1][i-j]=counte[1][i-(j+1)]
						counte[1][i-(j+1)]=temp1

		return counte

	def countsort(self,count):
		#print "countsort in progress"
		items=[]
		#print count
		for i in range(2,len(count[0])):
			pos=i
			items.append((count[0][pos],count[1][pos]))
		#print items
		items.sort(key=lambda item:item[1], reverse=True)
		#print items

		items=[(count[0][0],count[1][0]),(count[0][1],count[1][1])]+items

		return items
	def sort_by_value(self,d):
	    	""" Returns the keys of dictionary d sorted by their values """
	    	items=d.items()
	    	backitems=[ [v[1],v[0]] for v in items]
	    	backitems.sort()
	    	return [ backitems[i][1] for i in range(0,len(backitems))]
	def write(self,text,file,outfile="none"):
		if file == "y" :
			file=open(outfile,"w")
			file.write(text)
			file.close()
		else:
			print text

	def process(self,eingabe,s,k,w,O=False,ignoreWords=[], ignoreKanji=[]):
		#zusatz für ignorier Listen:
		self.ignore_words=ignoreWords
		self.ignore_kanji=ignoreKanji

		text="" #hier lokal
		if O:
			text=text+ eingabe + "\n"+"\n"		
		if s :
			text=text + self.space(eingabe) +"\n"+"\n"

		if w:
			count=self.wordcount(eingabe)
			sort=self.countsort(count)
			text=text +"Wortliste:"
			for i in sort:
				text=text +"\n"+ i[0]+" : "+str(i[1])
			text=text +"\n"
		if k :
			count=self.kanjicount(eingabe)
			sort=self.countsort(count)
			text=text +"Kanjiliste:"
			for i in sort:
				text=text +"\n"+ i[0]+" : "+str(i[1])
			text=text +"\n\n"
		return text
tools=tools()
if len(sys.argv)>=3:
	encoding=""
#if True :
	if "--help"in sys.argv or "--h" in sys.argv or "-h" in sys.argv or "--H"in sys.argv or "-H" in sys.argv or "--Help" in sys.argv :
		print '''Komandozeilen Argumente:
	--help, --h,-h,-H,--H,--Help dieser text
	--s 		leerzeichen hinzufügen
	--k 		Kanji zählen und ausgeben
	--w 		Wörter zählen und ausgeben
	--o <datei> 	Ausgabe Datei
	--f <datei>   	Eingabe Datei
	--t <text>    	Text(wenn keine Eingabe Datei)
	--e <encoding>	(euc-jp, shift-jis, utf-8 etc. Programm versucht 
			selbstständig Die Encodierung zu erkennen, 
			aber erkennt sie nicht immer. (macht nur sinn mit --f)
	--O		unbearbeiteten Text anzeigen

--f ist mächtiger als --t
Wenn weder --f noch --t vorhanden sind wird um eine Eingabe gebeten.
Ist keine Ausgabedatei (--o) angegeben, erfolgt die Ausgabe über die Konsole
--s,--k,--w können gleichzeitig benutzt werden, die Ausgaben werden hintereinander gehängt'''
		exit()
	if "--e" in sys.argv:
		pos=sys.argv.index("--e")
		encoding= sys.argv[pos+1]
	if "--f" in sys.argv:
		pos=sys.argv.index("--f")
		infile=open(sys.argv[pos+1])
		eingabe=UnicodeDammit(infile.read(),[encoding]).unicode_markup
	elif "--t" in sys.argv :
		pos=sys.argv.index("--t")
		eingabe= sys.argv[pos+1]
	else:
		eingabe=raw_input("Japanischen Text eingeben:")
	
	if "--O" in sys.argv :
		O=True
	if "--s" in sys.argv :
		s=True
	if "--k" in sys.argv :
		k=True
	if "--w" in sys.argv:
		w=True

	text = tools.process(eingabe,s,k,w,O)

	if "--o" in sys.argv:
		pos=sys.argv.index("--o")
		outfile=sys.argv[pos+1]
		tools.write(text,"y",outfile) #globale variable text
	else:
		tools.write(text,"n")
elif len(sys.argv)>=2:
		if "--help"in sys.argv or "--h" in sys.argv or "-h" in sys.argv or "--H"in sys.argv or "-H" in sys.argv or "--Help" in sys.argv :
			print '''Komandozeilen Argumente:
	--help, --h,-h,-H,--H,--Help dieser text
	--s 		leerzeichen hinzufügen
	--k 		Kanji zählen und ausgeben
	--w 		Wörter zählen und ausgeben
	--o <datei> 	Ausgabe Datei
	--f <datei>   	Eingabe Datei
	--t <text>    	Text(wenn keine Eingabe Datei)
	--e <encoding>	(euc-jp, shift-jis, utf-8 etc. Programm versucht 
			selbstständig Die Encodierung zu erkennen, 
			aber erkennt sie nicht immer. (macht nur sinn mit --f)
	--O		unbearbeiteten Text anzeigen

--f ist mächtiger als --t
Wenn weder --f noch --t vorhanden sind wird um eine Eingabe gebeten.
Ist keine Ausgabedatei (--o) angegeben, erfolgt die Ausgabe über die Konsole
--s,--k,--w können gleichzeitig benutzt werden, die Ausgaben werden hintereinander gehängt'''
			exit()
		else:	 #versuchen datei zu öffnen
			app = QtGui.QApplication(sys.argv)
			qb = Window()
			qb.show()
			try:
				fname=open(sys.argv[1])
				data= UnicodeDammit(fname.read())
				qb.textedit.setPlainText(data.unicode_markup)		
			except:
				try:
					fname=open("./"+sys.argv[1])
					data= UnicodeDammit(fname.read())
					qb.textedit.setPlainText(data.unicode_markup)
				except:
					print "fehler beim oeffnen"
			sys.exit(app.exec_())
else:
	app = QtGui.QApplication(sys.argv)
	qb = Window()
	qb.show()	
	sys.exit(app.exec_())
