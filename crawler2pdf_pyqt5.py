#requirement: python 3.6 
#brew install qt //5.10.1, should be >= 5.8
#pip3 install pyqt5 //5.10.1, should be >= 5.8
#pip install lxml requests PyPDF2 reportlab

import sys 
import os
import requests
import time
from lxml import html
from PyPDF2 import  PdfFileWriter, PdfFileMerger, PdfFileReader
from PyQt5 import QtGui,QtCore, QtWidgets, QtWebEngineWidgets
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

#用来作业完成后，定时关闭
class MyTimer(QtWidgets.QWidget):
    def __init__(self, parent = None):
        super(MyTimer, self).__init__(parent)      
        self.timer = QtCore.QTimer()      
        self.timer.setInterval(1000)       
        self.timer.timeout.connect(self.onTimerOut)
    def start(self):        
        self.count=10
        self.timer.start()
    def stop(self):        
        self.timer.stop()
    def onTimerOut(self):        
        self.count-=1
        print("close app after %d s"%(self.count))
        if self.count<=0:
            QtWidgets.qApp.quit()

class PDF(object):

    def __init__(self,pdfName):
        self._outPdfName=pdfName
        self._outPdf= PdfFileWriter()
        self._mergerPdfName="merger_"+pdfName
        self._mergerPdf = PdfFileMerger()
        self._pageNum = 0
        try:
            os.remove(self._outPdfName)
        except OSError:
            pass
        try:
            os.remove(self._mergerPdfName)
        except OSError:
            pass

    def write(self):
        self.addPageNum()
        with open(self._outPdfName,'wb') as fout:
            print("saving to [%s]..."%(self._outPdfName))
            if self._outPdf.getNumPages()>0:
                self._outPdf.write(fout)
            else:
                self._mergerPdf.write(self._mergerPdfName)
            print("saved [%s]"%(self._outPdfName))

    def append(self,newPdfName,bookmark=None):
        with open(newPdfName,'rb') as fnew:
            newpdf=PdfFileReader(fnew)
            # self._pageNum+=newpdf.getNumPages()
            # self._mergerPdf.append(newpdf)
            self._mergerPdf.append(newpdf,"hh")

    def addPageNum(self):
        numPdfName="num_"+self._outPdfName
        self._mergerPdf.write(self._mergerPdfName)
        #
        with open(self._mergerPdfName, 'rb') as fmerger:
            mergerpdf = PdfFileReader(fmerger,strict=False)
            n = mergerpdf.getNumPages()
            c = canvas.Canvas(numPdfName)
            for i in range(1,n+1): 
                #A4 199mm
                width=mergerpdf.getPage(0).mediaBox.getWidth()*0.352*0.95
                #A4 4.4mm
                height=mergerpdf.getPage(0).mediaBox.getHeight()*0.352*0.015
                c.drawString((width)*mm, (height)*mm, str(i))
                c.showPage()
            c.save()
            with open(numPdfName, 'rb') as fnum:
                numberPdf = PdfFileReader(fnum)
                for p in range(n):
                    print("add page number %d/%d to [%s]"%(p+1,n,self._outPdfName))
                    page = mergerpdf.getPage(p)
                    numberLayer = numberPdf.getPage(p)
                    page.mergePage(numberLayer)
                    self._outPdf.addPage(page)
            os.remove(numPdfName)

class WebPage(QtWebEngineWidgets.QWebEnginePage):

    global t
    def __init__(self):
        super(WebPage, self).__init__()
        #注册事件，并不是立即执行
        #完成加载后,触发fetchNext()
        self.loadFinished.connect(self.handleLoadFinished)
        #打印pdf后,触发合并pdf，不能加载后触发，那时最后一个pdf来不及打印
        self.pdfPrintingFinished.connect(self.appendpdf)

    def appendpdf(self,filename):
        self._pdf.append(filename)
        os.remove(filename)
        if not self.fetchNext():
            print('save merged pdfs to [%s]'%(self._pdfname))
            self._pdf.write()
            t.start()

    #第一次触发fetchNext()
    def start(self, urls,pdfname):
        self._urls = iter(urls)
        self._pdfname=pdfname
        self._pdf= PDF(pdfname)
        self.fetchNext()

    #加载网页load
    def fetchNext(self):
        t.stop()
        try:
            url = next(self._urls)
        except StopIteration:
            return False
        else:
            self.load(QtCore.QUrl(url))
        return True

    #删除MathJax_Message div，否则网页上会线上框，遮挡正文;不起作用，因为loadfinished时,js还在运行，会重新生成MathJax_Message div,有效方案参见set_MathJax_Message()
    def remove_MathJax_Message(self): 
        code = 'document.getElementById("MathJax_Message").remove();'
        self.runJavaScript(code)

    #全局设置MathJax_Message div 隐藏
    def set_MathJax_Message(self): 
        code = '''
function setcssrule(selectorText, style, value){
  var rules;
  for(var m in document.styleSheets){
    rules = document.styleSheets[m][document.all ? 'rules' : 'cssRules'];
    for(var n in rules){
      if(rules[n].selectorText == selectorText){
        rules[n].style[style]=value;
        return;
      }
    }
  }
}
setcssrule("#MathJax_Message","display","none")
'''
        self.runJavaScript(code)

    def printpdf(self, html):
        url = self.url().toString()
        pdfName=str(int(round(time.time() * 1000)))+".pdf"
        print('save [%d bytes %s] to [%s]' % (len(html),url,pdfName))
        self.printToPdf(pdfName, QtGui.QPageLayout(QtGui.QPageSize(QtGui.QPageSize.A4 ), QtGui.QPageLayout.Portrait, QtCore.QMarginsF(0,0,0,0)))

    #网页元素loadFinished时，和js/render是独立的，此时js不一定运行完，网页不一定渲染出来
    def handleLoadFinished(self):
        #waiting for parsing math formulas
        time.sleep(1)
        self.set_MathJax_Message()
        self.toHtml(self.printpdf)

def prasePytorchUrl(baseurl):
    page=requests.Session().get(baseurl) 
    htmlcontent=html.fromstring(page.text) 
    version=htmlcontent.xpath('//div[@class="version"]/text()')[0].replace(" ","").replace("\n","")
    aurl=htmlcontent.xpath('//li[contains(@class,"l1") or contains(@class,"l2")]/a/@href')
    outlineurl=[]
    #去重，去掉网页内的跳转链接
    [outlineurl.append(baseurl+str(val)) for val in aurl if str(val).count("#")==0 and not baseurl+str(val) in outlineurl]
    #加上起始页本身
    outlineurl.insert(0,baseurl)
    return outlineurl,version

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)

    #全局计时器，用于自动关闭app
    global t
    t=MyTimer()

    #pytorch docs
    # pytorchDocPage = WebPage()
    # pytorchDocUrl,pytorchDocVersion=prasePytorchUrl('https://pytorch.org/docs/stable/')
    # # pytorchDocPage.start(pytorchDocUrl[16:20],"test2_pytorch_docs_%s.pdf"%(pytorchDocVersion))
    # pytorchDocPage.start(pytorchDocUrl,"pytorch_docs_%s.pdf"%(pytorchDocVersion))

    #pytorch tutorials
    pytorchTutorialsPage = WebPage()
    pytorchTutorialsUrl,pytorchTutorialsVersion=prasePytorchUrl('https://pytorch.org/tutorials/')
    # pytorchTutorialsPage.start(pytorchTutorialsUrl[15:20],"test2_pytorch_tutorials_%s.pdf"%(pytorchTutorialsVersion))
    pytorchTutorialsPage.start(pytorchTutorialsUrl,"pytorch_tutorials_%s.pdf"%(pytorchTutorialsVersion))

    #以上是窗口程序的定义，exec才开始运行
    sys.exit(app.exec())
