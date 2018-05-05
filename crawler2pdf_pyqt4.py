#requirement: python 3.5 
#1) conda create --name python35 python=3.5 
#2) source activate python35
#conda install pyqt=4.11
#pip install lxml requests PyPDF2
#cann't prase math formulas right, image was split into two pages

import sys,os,requests,time
from lxml import html
from PyQt4 import QtCore,QtGui,QtWebKit
from PyPDF2 import PdfFileMerger,PdfFileReader

class WebPage(QtWebKit.QWebPage):
    def __init__(self):
        super(WebPage, self).__init__()
        # self.mainFrame().loadFinished.connect(self.handleLoadFinished)
        QtCore.QObject.connect(self.mainFrame(), QtCore.SIGNAL("loadFinished(bool)"),self.handleLoadFinished)
        self.printer = QtGui.QPrinter()
        self.printer.setPageSize(QtGui.QPrinter.A4)
        self.printer.setOrientation(QtGui.QPrinter.Landscape)
        self.printer.setOutputFormat(QtGui.QPrinter.PdfFormat)
        # self.printer.setPageMargins(0,0,0,0,QtGui.QPrinter.Millimeter)

    def start(self, urls,finalFile):
        self._urls = iter(urls)
        self.finalFile= finalFile
        self.merger = PdfFileMerger()
        try:
            os.remove(self.finalFile)
        except OSError:
            pass
        self.fetchNext()

    def fetchNext(self):
        try:
            url = next(self._urls)
        except StopIteration:
            return False
        else:
            self.mainFrame().load(QtCore.QUrl(url))
        return True

    def processCurrentPage(self):
        url = self.mainFrame().url().toString()
        # html = self.mainFrame().toHtml()
        pdfname=str(int(round(time.time() * 1000)))+".pdf"
        self.printer.setOutputFileName(pdfname)
        self.mainFrame().print_(self.printer)
        self.merger.append(PdfFileReader(open(pdfname, 'rb')))
        os.remove(pdfname)
        print('save [%d bytes %s] to [%s]' % (self.bytesReceived(),url,pdfname))

    def handleLoadFinished(self):
        time.sleep(15)
        self.processCurrentPage()
        if not self.fetchNext():
            self.merger.write(self.finalFile)
            print('combine pdfs to [%s]' % (self.finalFile))
            QtGui.qApp.exit()

def getoutlineurl(baseurl):
    page=requests.Session().get(baseurl) 
    htmlcontent=html.fromstring(page.text) 
    version=htmlcontent.xpath('//div[@class="version"]/text()')[0].replace(" ","").replace("\n","")
    aurl=htmlcontent.xpath('//li[contains(@class,"l1") or contains(@class,"l2")]/a/@href')
    outlineurl=[baseurl+str(val) for val in aurl if str(val).count("#")==0]
    outlineurl.insert(0,baseurl)
    return outlineurl,version

if __name__ == '__main__':
    
    app = QtGui.QApplication(sys.argv)

    webpage1 = WebPage()
    tutorialsOutlineUrl,tutorialsVersion=getoutlineurl('https://pytorch.org/tutorials/')
    webpage1.start(tutorialsOutlineUrl[17:20],"pytorch_tutorials_%s.pdf"%(tutorialsVersion))

    # webpage2 = WebPage()
    # docOutlineUrl,docVersion=getoutlineurl('https://pytorch.org/docs/stable/')
    # webpage2.start(docOutlineUrl,"pytorch_doc_%s.pdf"%(docVersion))

    app.exec_()
    # sys.exit(app.exec_())
