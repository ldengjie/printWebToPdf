#requirement: python 3.6 
#brew install qt //5.10.1, should be >= 5.8
#pip3 install pyqt5 //5.10.1, should be >= 5.8
#pip install lxml requests PyPDF2 reportlab
#in PDF class don't use "with" to open pdf file otherwise it will lead to confusion. 
#qt version shoule be >=5.8 otherwise an image will break into multiple pages.

import sys 
import os
import requests
import time
from lxml import html
from PyPDF2 import  PdfFileWriter, PdfFileMerger, PdfFileReader
from PyQt5 import QtGui,QtCore, QtWidgets, QtWebEngineWidgets
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor

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

    def __init__(self,version,urls,pdfName,texts,levels):
        self._urls=urls
        self._version=version
        self._outPdfName=pdfName
        self._outPdf= PdfFileWriter()
        self._mergerPdfName="merger_"+self._outPdfName
        self._mergerPdf = PdfFileMerger()
        self._mergerPageNum = 0
        self._outlinePdfName="outline_"+self._outPdfName
        self._outlinePageNum=0
        self._numPdfName="num_"+self._outPdfName
        self._pos= []
        self._texts= texts
        self._levels= levels
        try:
            os.remove(self._outPdfName)
        except OSError:
            pass
        try:
            os.remove(self._mergerPdfName)
        except OSError:
            pass

    def write(self):
        self.addOutline()
        self.addPageNum()
        self.addBookmark()
        print("save [%s]..."%(self._outPdfName))
        self._outPdf.write(open(self._outPdfName,'wb'))

    def append(self,newPdfName,bookmark=None):
        with open(newPdfName,'rb') as fnew:
            newpdf=PdfFileReader(fnew)
            self._pos.append(self._mergerPageNum)
            self._mergerPageNum+=newpdf.getNumPages()
            self._mergerPdf.append(newpdf)

    def addOutline(self):
        print("add outline to [%s]"%(self._outPdfName))
        coutline = canvas.Canvas(self._outlinePdfName,pagesize=A4)
        coutline.drawString((100)*mm, (275)*mm, "Outline")
        posi=0
        for pi in range(len(self._texts)):
            text=self._texts[pi]
            level=self._levels[pi]
            if level==2 or text=="Introduction":
                pos=self._pos[posi]+1
                posi+=1
                lineStr=" "*8*(level-1)+text+" "*4+str(pos)
            else:
                lineStr=" "*8*(level-1)+text
            height=(250-10*(pi+1))%250+20
            coutline.drawString((30)*mm, (height)*mm, lineStr)
            if height == 20:
                coutline.showPage()
            #增加网址和邮箱信息
            if pi==len(self._texts)-1:
                coutline.setFont('Helvetica',9)
                coutline.setFillColor(HexColor(0xff8100))
                pi+=1
                height=(250-10*(pi+1))%250+20
                lineStr="Printed v"+self._version+" from [ "+self._urls[0]+" ] at "+time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())+"."
                coutline.drawString((30)*mm, (height)*mm, lineStr)
                height-=5
                lineStr="Visit [ https://download.csdn.net/user/ldengjie/uploads ] to get the latest version pdf"
                coutline.drawString((30)*mm, (height)*mm, lineStr)
                height-=5
                lineStr="or mail to ldengjie@163.com to ask for printing and updating the latest version pdf."
                coutline.drawString((30)*mm, (height)*mm, lineStr)
        coutline.showPage()
        coutline.save()

        outlinePdf = PdfFileReader(open(self._outlinePdfName, 'rb'),strict=False)
        self._outlinePageNum=outlinePdf.getNumPages()
        
        for ci in range(self._outlinePageNum):
            self._outPdf.addPage(outlinePdf.getPage(ci))
        os.remove(self._outlinePdfName)

    def addPageNum(self):
        self._mergerPdf.write(self._mergerPdfName)
        mergerpdf = PdfFileReader(open(self._mergerPdfName, 'rb'),strict=False)
        n = mergerpdf.getNumPages()
        c = canvas.Canvas(self._numPdfName)
        for i in range(1,n+1): 
            #A4 199mm
            width=mergerpdf.getPage(0).mediaBox.getWidth()*0.352*0.95
            #A4 4.4mm
            height=mergerpdf.getPage(0).mediaBox.getHeight()*0.352*0.015
            c.drawString((width)*mm, (height)*mm, str(i))
            c.showPage()
        c.save()
        numberPdf = PdfFileReader(open(self._numPdfName, 'rb'))
        for p in range(n):
            print("add page number %d/%d to [%s]"%(p+1,n,self._outPdfName),end='\r')
            page = mergerpdf.getPage(p)
            numberLayer = numberPdf.getPage(p)
            page.mergePage(numberLayer)
            self._outPdf.addPage(page)
        print("")
        os.remove(self._numPdfName)

    def addBookmark(self):
        print("add bookmark to [%s]"%(self._outPdfName))
        parent=self._outPdf.addBookmark("Outline",0,None)
        posi=0
        for ti in range(len(self._texts)):
            text=self._texts[ti]
            level=self._levels[ti]
            pos=self._pos[posi]+self._outlinePageNum
            if level==2 or text=="Introduction":
                posi+=1
            level=self._levels[ti]
            if level==1:
               parent=self._outPdf.addBookmark(text,pos,None)
            elif level==2:
               child=self._outPdf.addBookmark(text,pos,parent)

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
        # os.remove(filename)
        if not self.fetchNext():
            print('save merged pdfs to [%s]'%(self._pdfname))
            self._pdf.write()
            t.start()

    #第一次触发fetchNext()
    def start(self,version,urls,texts,levels,pdfname):
        self._urls = iter(urls)
        self._pdfname=pdfname.replace(".pdf","_")+version+".pdf"
        self._pdf= PDF(version,urls,self._pdfname,texts,levels)
        self.fetchNext()

    #加载网页load
    def fetchNext(self):
        t.stop()
        try:
            url = next(self._urls)
        except StopIteration:
            return False
        else:
            if url.count("nourl")>0:
                self.fetchNext()
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

    #删除元素;footer需要倒序删除:1->0,或0->0,删除一个后,后续元素会自动前移，也不能放在for循环里;
    def delete_element(self): 
        code = '''
document.getElementById("header-holder").remove();

document.querySelectorAll('.table-of-contents-link-wrapper').forEach(function(a) {
  a.remove()
})

document.getElementById("pytorch-content-right").remove();

document.getElementById("docs-tutorials-resources").remove();

var ele = document.getElementsByTagName("footer");
ele[1].parentNode.removeChild(ele[1]);
ele[0].parentNode.removeChild(ele[0]);
'''
        self.runJavaScript(code)

    def printpdf(self, html):
        url = self.url().toString()
        pdfName=str(int(round(time.time() * 1000)))+".pdf"
        print('save [%d bytes %s] to [%s]' % (len(html),url,pdfName))
        self.printToPdf(pdfName, QtGui.QPageLayout(QtGui.QPageSize(QtGui.QPageSize.A4), QtGui.QPageLayout.Portrait, QtCore.QMarginsF(0,0,0,0)))

    #网页元素loadFinished时，和js/render是独立的，此时js不一定运行完，网页不一定渲染出来
    def handleLoadFinished(self):
        self.set_MathJax_Message()
        self.delete_element()
        #waiting for parsing math formulas
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(5000, loop.quit);
        loop.exec_()
        self.toHtml(self.printpdf)


def prasePytorchUrl(baseurl):
    page=requests.Session().get(baseurl) 
    htmlcontent=html.fromstring(page.text) 
    version=htmlcontent.xpath('//div[@class="version"]/text()')[0].replace(" ","").replace("\n","")
    aclass=htmlcontent.xpath('//span[contains(@class,"caption") and text()!=""]/@class|//li[contains(@class,"l1") and a/text()!="" ]/@class')
    aurl=htmlcontent.xpath('//li[contains(@class,"l1")]/a[text()!=""]/@href')
    atext=htmlcontent.xpath('//li[contains(@class,"l1")]/a[text()!=""]/text()|//span[contains(@class,"caption") and text()!=""]/text()')
    #去重，去掉网页内的跳转链接
    # [outlineurl.append(baseurl+str(val)) for val in aurl if str(val).count("#")==0 and not baseurl+str(val) in outlineurl]
    outlineurl=[]
    outlinetext=[]
    outlinelevel=[]
    print("len(aurl)",len(aurl))
    print("len(aclass)",len(aclass))
    print("len(atext)",len(atext))
    urli=0
    for ui in range(len(aclass)):
        text=str(atext[ui])
        classStr=str(aclass[ui])
        if classStr.count("l1")>0:
            urlStr=baseurl+str(aurl[urli])
            urli+=1
        else:
            urlStr="nourl"+str(ui)
        if urlStr.count("#")==0 and not urlStr in outlineurl:
            outlineurl.append(urlStr)
            outlinetext.append(text)
            if classStr.count("l1")>0:
                outlinelevel.append(2)
            else:
                outlinelevel.append(1)
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

    #pytorch tutorials
    pytorchTutorialsPage = WebPage()
    pytorchTutorialsUrl,pytorchTutorialsText,pytorchTutorialsLevel,pytorchTutorialsVersion=prasePytorchUrl('https://pytorch.org/tutorials/')
    print("== pytorchTutorialsUrl: \n",pytorchTutorialsUrl)
    print("== pytorchTutorialsText: \n",pytorchTutorialsText)
    print("== pytorchTutorialsLevel: \n",pytorchTutorialsLevel)
    print("== pytorchTutorialsVersion: \n",pytorchTutorialsVersion)
    pytorchTutorialsPage.start(pytorchTutorialsVersion,pytorchTutorialsUrl,pytorchTutorialsText,pytorchTutorialsLevel,"pytorch_tutorials.pdf")

    #以上是窗口程序的定义，exec才开始运行
    sys.exit(app.exec())
