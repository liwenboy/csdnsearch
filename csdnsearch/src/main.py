# -*- encoding:utf-8  -*-

import wx,requests,re,threading
from collections import  namedtuple
from enum import Enum
from HTMLParser import  HTMLParser
from wx import _windows_, wxEVT_HOTKEY

T_USERAGENT="Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0"
RE_LISTCONTENT=r'(?P<content><dl class="search-list.*?</dl> -->.*)+'
RE_LISTEXTRACT=r'<dd.*?<dt.*?<a.*?href="(?P<url>.*?)".*?>(?P<title>.*?)</a>'
RE_ARTICLECONTENT=[r'<article>(?P<content>.*?)</article>',
                   r'<body>(?P<content>.*?)</body>',]


ResItem=namedtuple("ResItem","title url details")
HOTKEYID=wx.NewId()

class MainFrame(wx.Frame):
    def __init__(self):
        super(MainFrame,self).__init__(parent=None,
                                       title=u"CSDN 博客搜索",size=(800,600))
        self.Center()
        
        self.panel=wx.Panel(self)
        self.tc=wx.TextCtrl(self.panel,style=wx.TE_PROCESS_ENTER)
        self.srchbtn=wx.Button(self.panel,label=u"搜索(&S)")
        self.lc=wx.ListCtrl(self.panel,style=wx.LC_REPORT | wx.LC_NO_HEADER)
        self.prebtn=wx.Button(self.panel,label=u"上一页(&P)")
        self.prebtn=wx.Button(self.panel,label=u"上一页(&P)")
        self.nextbtn=wx.Button(self.panel,label=u"下一页(&N)")
        self.srchbtn.Bind(wx.EVT_BUTTON,self.srchbtnclick)
        self.tc.Bind(wx.EVT_TEXT_ENTER,self.srchbtnclick)
        self.prebtn.Bind(wx.EVT_BUTTON,self.prebtnclick)
        self.nextbtn.Bind(wx.EVT_BUTTON,self.nextbtnclick)
        self.lc.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.itemactivated)
        self.lc.Bind(wx.EVT_KEY_DOWN,self.keydown)
        self.Bind(wx.EVT_HOTKEY,self.hotkey)
        self.RegisterHotKey(HOTKEYID,0,120)
        
        self.mainurl="http://so.csdn.net/so/search/s.do"
        self.resiteems=[]
        self.srchstring=""
        self.pagenum=1
        
        self.layout()
        
    def srchbtnclick(self,evt):
        text=self.tc.Value.strip()
        if  text:
            self.srchstring=text
            self.pagenum=1
            SearchThread(self,self.mainurl,self.srchstring,self.pagenum).start()
            self.lc.SetFocus()
    
    def prebtnclick(self,evt):
        if self.srchstring !="" and self.pagenum >1:
            self.pagenum-=1
            SearchThread(self,self.mainurl,self.srchstring,self.pagenum).start()
            self.lc.SetFocus()
    
    def nextbtnclick(self,evt):
        if self.srchstring !="":
            self.pagenum+=1
            SearchThread(self,self.mainurl,self.srchstring,self.pagenum).start()
            self.lc.SetFocus()
    
    def itemactivated(self,evt):
        r=self.resiteems[evt.GetIndex()]
        ShowtextThread(self,r.url,r.title).start()
        
    def keydown(self,evt):
        if evt.KeyCode==ord("D") and evt.altDown:
            self.tc.SetFocus()
            self.tc.SelectAll()
        if evt.KeyCode==wx.WXK_PAGEUP:
            self.prebtnclick(None)
        if evt.KeyCode==wx.WXK_PAGEDOWN:
            self.nextbtnclick(None)
        evt.Skip()
    
    def hotkey(self,evt):
        if self.IsShown(): self.Hide()
        else:  self.Show()
        evt.Skip()            
    
    def updatelist(self):
        self.lc.ClearAll()
        self.lc.InsertColumn(0,"",width=600)
        for i,item in enumerate([j.title for j in self.resiteems]):
            self.lc.InsertStringItem(i,item)
        
    def showtext(self,title,text):
        ShowtextFrame(self,title,text).Show()
    
    def layout(self):
        self.hszer1=wx.BoxSizer(wx.HORIZONTAL)
        self.hszer1.Add(self.tc,1,flag=wx.GROW)
        self.hszer1.Add(self.srchbtn,flag=wx.ALIGN_RIGHT)
        self.hszer2=wx.BoxSizer(wx.HORIZONTAL)
        self.hszer2.Add(self.prebtn,flag=wx.ALIGN_LEFT)
        self.hszer2.Add(wx.Size(80,20),1,wx.GROW)
        self.hszer2.Add(self.nextbtn,flag=wx.ALIGN_RIGHT)
        self.vszer=wx.BoxSizer(wx.VERTICAL)
        self.vszer.Add(self.hszer1,flag=wx.GROW)
        self.vszer.Add(self.lc,1,flag=wx.GROW)
        self.vszer.Add(self.hszer2,flag=wx.GROW)
        self.panel.SetSizer(self.vszer)
        self.panel.Fit()
        
class SearchThread(threading.Thread):
    def __init__(self,window,url,srchstring,pagenum):
        super(SearchThread,self).__init__()
        self.window=window
        self.url=url
        self.srchstring=srchstring
        self.pagenum=pagenum
        
    def run(self):
        self.window.resiteems=list()
        try:
            html=requests.get(self.url,
                              params={"t":"blog","q":self.srchstring,"p":self.pagenum},
                              headers={"User-Agent":T_USERAGENT}).text
        except Exception as e:
            wx.MessageBox(u"网络连接异常！",u"CSDN 博客搜索")
            return None
            
        try:
            content=re.compile(RE_LISTCONTENT,re.S).search(html).group("content")
            matchs=re.compile(RE_LISTEXTRACT, re.S).finditer(content)
        except Exception as e:
            wx.MessageBox(u"网页解析出错！")
            return None
            
        if matchs:
            for m in matchs:
                title=m.group("title").replace("<em>","").replace("</em>","")
                resitem=ResItem._make([title,m.group("url"),""])
                self.window.resiteems.append(resitem)
                wx.CallAfter(self.window.updatelist)
        
class ShowtextThread(threading.Thread):
    def __init__(self,window,url,title):
        super(ShowtextThread,self).__init__()
        self.window=window
        self.url=url
        self.title=title
    def run(self):
        try:
            html=requests.get(self.url,headers={"User-Agent":T_USERAGENT}).text
#             STD(html).ShowModal()
            
        except:
            wx.MessageBox(u"网络连接异常！",u"CSDN 博客搜索")
            return None
            
        for rt in RE_ARTICLECONTENT:
            m=re.compile(rt, re.S).search(html)
            if m:    break
             
        text=m.group("content")
        
        text=re.compile(r'<[^>]*?>').sub("",text)
        text=HTMLParser().unescape(text)
        text=re.compile(r'(\n+)|((\r\n)+)').sub(r'\n',text)
        
        wx.CallAfter(self.window.showtext,self.title,text)
        
class ShowtextFrame(wx.Frame):
    def __init__(self,parent,title,text):
        super(ShowtextFrame,self).__init__(
            parent=parent,title=title,size=(800,600))
        self.Center()
        
        self.panel=wx.Panel(self)
        self.tc=wx.TextCtrl(self.panel,style=wx.TE_MULTILINE)
        self.tc.Bind(wx.EVT_KEY_DOWN,self.keydown)
        self.tc.SetValue(text)
        
        self.szer=wx.GridSizer(0,0,10,10)
        self.szer.Add(self.tc,flag=wx.GROW)
        self.panel.SetSizer(self.szer)
        self.panel.Fit()
        
    def keydown(self,evt):
        if evt.KeyCode in (wx.WXK_ESCAPE,wx.WXK_BACK,wx.WXK_RETURN):
            self.Close()
        if evt.GetKeyCode() ==ord("C") and evt.controlDown:
            if wx.TheClipboard.Open():
                self.tc.SelectAll()
                wx.TheClipboard.SetData(wx.TextDataObject(self.tc.Value))
                wx.TheClipboard.Close()
        evt.Skip()
        
class STD(wx.Dialog):
    def __init__(self,text):
        super(STD,self).__init__(None,-1,"ShowText")
        tc=wx.TextCtrl(self,value=text,style=wx.TE_MULTILINE)
        
class ThisApp(wx.App):
    def OnInit(self):
        self.mf=MainFrame()
        self.SetTopWindow(self.mf)
        self.mf.Show()
        return True 
    
def main():
    app=ThisApp()
    app.MainLoop()
    
if __name__=="__main__":
    main()
    
