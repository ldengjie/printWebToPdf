#requirement: python 3.6 
#brew install qt //5.10.1, should be >= 5.8
#pip3 install pyqt5 //5.10.1, should be >= 5.8
#pip install lxml requests PyPDF2 reportlab

import sys 
import os
import requests
import time
from lxml import html
from PyPDF2 import  PdfFileWriter,PdfFileMerger, PdfFileReader
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

class WebPage(QtWebEngineWidgets.QWebEnginePage):

    global t
    def __init__(self):
        super(WebPage, self).__init__()
        #注册事件，并不是立即执行
        #完成加载后,触发fetchNext()
        self.loadFinished.connect(self.handleLoadFinished)
        #打印pdf后,触发合并pdf，不能加载后触发，那时最后一个pdf来不及打印
        self.pdfPrintingFinished.connect(self.mergepdf)

    def mergepdf(self,filename):
        self.merger.append(PdfFileReader(open(filename, 'rb')))
        os.remove(filename)
        if not self.fetchNext():
            print('merge pdfs to [%s]'%(self.finalFile))
            self.merger.write(self.finalFile)
            self.addPageNumToPdf(self.finalFile)
            t.start()

    def addPageNumToPdf(self, finalFile):
        finalFileWithNum=finalFile.replace(".pdf","")+"_withPageNum.pdf"
        try:
            os.remove(finalFileWithNum)
        except OSError:
            pass
        output = PdfFileWriter()
        with open(finalFile, 'rb') as f:
            pdf = PdfFileReader(f,strict=False)
            n = pdf.getNumPages()
            tmp="pagenumber_"+finalFile
            c = canvas.Canvas(tmp)
            for i in range(1,n+1): 
                #A4大小210*297mm,后续可以通过QWebEnginePage自动判断纸张大小,-10mm
                c.drawString((200)*mm, (4)*mm, str(i))
                c.showPage()
            c.save()
            with open(tmp, 'rb') as ftmp:
                numberPdf = PdfFileReader(ftmp)
                for p in range(n):
                    print("add page number %d/%d to [%s]"%(p+1,n,finalFile))
                    page = pdf.getPage(p)
                    numberLayer = numberPdf.getPage(p)
                    page.mergePage(numberLayer)
                    output.addPage(page)
            with open(finalFileWithNum,'wb') as f:
                print("saving to [%s]..."%(finalFileWithNum))
                output.write(f)
                print("saved [%s]"%(finalFileWithNum))
            os.remove(tmp)

    #第一次触发fetchNext()
    def start(self, urls,finalFile):
        self._urls = iter(urls)
        self.finalFile= finalFile
        self.merger = PdfFileMerger()
        try:
            os.remove(self.finalFile)
        except OSError:
            pass
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
        pdfname=str(int(round(time.time() * 1000)))+".pdf"
        print('save [%d bytes %s] to [%s]' % (len(html),url,pdfname))
        self.printToPdf(pdfname, QtGui.QPageLayout(QtGui.QPageSize(QtGui.QPageSize.A4 ), QtGui.QPageLayout.Portrait, QtCore.QMarginsF(0,0,0,0)))

    #网页元素loadFinished时，和js/render是独立的，此时js不一定运行完，网页不一定渲染出来
    def handleLoadFinished(self):
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

    #pytorch doc
    pytorchDocPage = WebPage()
    pytorchDocUrl,pytorchDocVersion=prasePytorchUrl('https://pytorch.org/docs/stable/')
    # pytorchDocPage.start(pytorchDocUrl[16:20],"test2_pytorch_doc_%s.pdf"%(pytorchDocVersion))
    pytorchDocPage.start(pytorchDocUrl,"pytorch_doc_%s.pdf"%(pytorchDocVersion))

    #pytorch tutorials
    pytorchTutorialsPage = WebPage()
    pytorchTutorialsUrl,pytorchTutorialsVersion=prasePytorchUrl('https://pytorch.org/tutorials/')
    # pytorchTutorialsPage.start(pytorchTutorialsUrl[16:20],"test2_pytorch_tutorials_%s.pdf"%(pytorchTutorialsVersion))
    pytorchTutorialsPage.start(pytorchTutorialsUrl,"pytorch_tutorials_%s.pdf"%(pytorchTutorialsVersion))

    #以上是窗口程序的定义，exec才开始运行
    sys.exit(app.exec())
