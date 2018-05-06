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
from reportlab.lib.pagesizes import A4

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
        with open(filename, 'rb') as f:
            pdf = PdfFileReader(f,strict=False)
            self._pos.append(self._num)
            self._num+=pdf.getNumPages()
            self.merger.append(pdf)
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

        outlinepage="outline_"+finalFile
        coutline = canvas.Canvas(outlinepage,pagesize=A4)
        coutline.drawString((100)*mm, (275)*mm, "Outline")
        for pi in range(len(self._texts)):
            text=self._texts[pi]
            pos=self._pos[pi]+1
            level=self._levels[pi]
            lineStr=" "*8*(level-1)+text+" "*4+str(pos)
            height=(250-10*(pi+1))%250+20
            coutline.drawString((30)*mm, (height)*mm, lineStr)
            if height == 20:
                coutline.showPage()
        coutline.showPage()
        coutline.save()

        cpage = PdfFileReader(open(outlinepage, 'rb'),strict=False)
        cpagenum=cpage.getNumPages()
        
        for ci in range(cpagenum):
            output.addPage(cpage.getPage(ci))

        pdf = PdfFileReader(open(finalFile, 'rb'),strict=False)
        n = pdf.getNumPages()
        tmp="pagenumber_"+finalFile
        c = canvas.Canvas(tmp)
        for i in range(1,n+1): 
            #A4大小210*297mm,后续可以通过QWebEnginePage自动判断纸张大小,-10mm
            c.drawString((200)*mm, (4)*mm, str(i))
            c.showPage()
        c.save()
        numberPdf = PdfFileReader(open(tmp, 'rb'))
        for p in range(n):
            print("add page number %d/%d to [%s]"%(p+1,n,finalFile))
            page = pdf.getPage(p)
            numberLayer = numberPdf.getPage(p)
            page.mergePage(numberLayer)
            output.addPage(page)
        os.remove(tmp)

        print("saving to [%s]..."%(finalFileWithNum))
        for ti in range(len(self._texts)):
            text=self._texts[ti]
            pos=self._pos[ti]+cpagenum
            level=self._levels[ti]
            if level==1:
               parent=output.addBookmark(text,pos,None)
            elif level==2:
               child=output.addBookmark(text,pos,parent)
            # output.addBookmark(self._texts[ti],self._pos[ti])
        output.write(open(finalFileWithNum,'wb'))
        print("saved [%s]"%(finalFileWithNum))

    #第一次触发fetchNext()
    def start(self, urls,texts,levels,finalFile):
        self._urls = iter(urls)
        self._texts= texts
        self._levels= levels
        self._num=0
        self._pos=[]
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
        #waiting for parsing math formulas
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(1000, loop.quit);
        loop.exec_()
        self.toHtml(self.printpdf)

def prasePytorchUrl(baseurl):
    page=requests.Session().get(baseurl) 
    htmlcontent=html.fromstring(page.text) 
    version=htmlcontent.xpath('//div[@class="version"]/text()')[0].replace(" ","").replace("\n","")
    aclass=htmlcontent.xpath('//li[(contains(@class,"l1") or contains(@class,"l2")) and a/text()!="" ]/@class')
    aurl=htmlcontent.xpath('//li[contains(@class,"l1") or contains(@class,"l2")]/a[text()!=""]/@href')
    atext=htmlcontent.xpath('//li[contains(@class,"l1") or contains(@class,"l2")]/a[text()!=""]/text()')
    # atext=htmlcontent.xpath('//li[contains(@class,"l1") or contains(@class,"l2")]/a/span/text()')
    #去重，去掉网页内的跳转链接
    # [outlineurl.append(baseurl+str(val)) for val in aurl if str(val).count("#")==0 and not baseurl+str(val) in outlineurl]
    outlineurl=[]
    outlinetext=[]
    outlinelevel=[]
    for ui in range(len(aurl)):
        urlStr=baseurl+str(aurl[ui])
        text=str(atext[ui])
        classStr=str(aclass[ui])
        if urlStr.count("#")==0 and not urlStr in outlineurl:
            outlineurl.append(urlStr)
            outlinetext.append(text)
            if classStr.count("l1")>0:
                outlinelevel.append(1)
            elif classStr.count("l2")>0:
                outlinelevel.append(2)
            else:
                outlinelevel.append(0)
    #加上起始页本身
    outlineurl.insert(0,baseurl)
    outlinetext.insert(0,"Introduction")
    outlinelevel.insert(0,1)
    return outlineurl,outlinetext,outlinelevel,version

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)

    #全局计时器，用于自动关闭app
    global t
    t=MyTimer()

    #pytorch docs
    pytorchDocsPage = WebPage()
    pytorchDocsUrl,pytorchDocsText,pytorchDocsLevel,pytorchDocsVersion=prasePytorchUrl('https://pytorch.org/docs/stable/')
    pytorchDocsPage.start(pytorchDocsUrl,pytorchDocsText,pytorchDocsLevel,"pytorch_docs_%s.pdf"%(pytorchDocsVersion))

    #pytorch tutorials
    # pytorchTutorialsPage = WebPage()
    # pytorchTutorialsUrl,pytorchTutorialsText,pytorchTutorialsLevel,pytorchTutorialsVersion=prasePytorchUrl('https://pytorch.org/tutorials/')
    # pytorchTutorialsPage.start(pytorchTutorialsUrl,pytorchTutorialsText,pytorchTutorialsLevel,"pytorch_tutorials_%s.pdf"%(pytorchTutorialsVersion))

    #以上是窗口程序的定义，exec才开始运行
    sys.exit(app.exec())
