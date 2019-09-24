#  -*-    coding:UTF-8    -*-

import wx
import threading
import requests
import re
from collections import namedtuple

TITLE="CSDN_博客搜索"
MAINURL="http://so.csdn.net/so/search/s.do?"
USERAGENT="Mozilla/5.0 (Windows NT 6.1; rv:52.0) Gecko/20100101 Firefox/52.0"
FIRSTSRCH,ADDMORE,SHOWTEXT=tuple(range(3))
Item=namedtuple("Item", "title url")

class MainFrame(wx.Frame):

    def __init__ (self):
        super().__init__(None, -1, title=TITLE, size=(800, 600))
        self.Center()
        self.panel=wx.Panel(self)
        self.tc=wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.btn=wx.Button(self.panel, label=u"搜索(&S)")
        self.lc=wx.ListCtrl(self.panel, style=wx.LC_REPORT | \
                            wx.LC_NO_HEADER | wx.LC_SINGLE_SEL)
        self.std=ShowText(self)
        
        self.btn.Bind(wx.EVT_BUTTON, self.btnDown)
        self.tc.Bind(wx.EVT_TEXT_ENTER, self.btnDown)
        self.lc.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.itemactivated)
        self.lc.Bind(wx.EVT_CONTEXT_MENU, self.onpopmenu)

        self.creatememu()
        self.layout()
        
    def creatememu(self):
        self._pm=wx.Menu()
        browser=self._pm.Append(-1, "浏览器打开(&o)")
        self.Bind(wx.EVT_MENU, self.brsopen, browser)
        
    def brsopen(self, evt):
        from webbrowser import open
        open(self.Items[self.lc.GetFocusedItem()].url)
        
    def onpopmenu(self, evt):
        if self.lc.GetFocusedItem() in range(self.lc.GetItemCount()-1):
            self.lc.PopupMenu(self._pm)
    
    def btnDown(self,evt):
        self.strSrch=self.tc.Value.strip()
        if self.strSrch:
            self.state=FIRSTSRCH
            self.pagenum=1
            urltail=f"q={self.strSrch}&t=blog&o=&s=&l=&f=&p={self.pagenum}"
            GetHtml(self, MAINURL+urltail).start()
        
    def addmore(self):
        self.state=ADDMORE
        self.pagenum+=1
        urltail=f"q={self.strSrch}&t=blog&o=&s=&l=&f=&p={self.pagenum}"
        GetHtml(self, MAINURL+urltail).start()
        
    def itemactivated(self, evt):
        self.idx=evt.GetIndex()
        if self.lc.GetItem(self.idx).GetText()==u'加载更多...':
            self.addmore()
        else:
            self.state=SHOWTEXT
            GetHtml(self, self.Items[self.idx].url).start()
        
    def updatelist(self):
        self.lc.ClearAll()
        self.lc.InsertColumn(0, "", width=1000 )
        for i,item in enumerate(j.title for j in self.Items):
            self.lc.InsertItem(i,item)
        from sys import maxsize
        self.lc.InsertItem(maxsize,'加载更多...')
        self.lc.SetFocus()
        idx=0 if self.state==FIRSTSRCH else self.idx
        self.lc.Focus(idx)
        
    def NetBack(self, html):
        if self.state in (FIRSTSRCH, ADDMORE):
            self.Items=[] if self.state==FIRSTSRCH else self.Items
            lst=parsehtmltolist(html)
            if lst is None:
                wx.MessageBox("解析出错！", "提示：")
            else:
                self.Items.extend([Item._make(i) for i in lst])
                self.updatelist()
        elif self.state==SHOWTEXT:
            s=prettyhtml(html)
            if s:
                self.std.updatetext(self.Items[self.idx].title, s)
                self.std.ShowModal()
            else:
                wx.MessageBox("解析出错！", "提示：")

    def layout(self):
        hszer=wx.BoxSizer(wx.HORIZONTAL)
        hszer.Add(self.tc,1,flag=wx.GROW)
        hszer.Add(self.btn,flag=wx.ALIGN_RIGHT)
        vszer=wx.BoxSizer(wx.VERTICAL)
        vszer.Add(hszer,flag=wx.GROW)
        vszer.Add(self.lc,1,flag=wx.GROW)
        self.panel.SetSizer(vszer)

class GetHtml(threading.Thread):
    
    def __init__(self, window, url):
        super().__init__()
        self.window, self.url=window, url
        
    def run(self):
        html=""
        try:
            html=requests.get(self.url, \
                            headers={"User-Agent": USERAGENT}).text
            if html:
                wx.CallAfter(self.window.NetBack, html)
        except Exception as e:
            print(str(e))
            wx.MessageBox("网络异常！", "提示：")
            
class ShowText(wx.Dialog):
    
    def __init__(self, parent):
        super().__init__(parent=parent, size=(800, 600), style=wx.DEFAULT_FRAME_STYLE)
        self.Center()
        self.tc=wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self.tc.Bind(wx.EVT_KEY_DOWN, self.kd)
        self.Bind(wx.EVT_CLOSE, self.onclose)
        
    def updatetext(self, title, text):
        self._title, self._text=title, text
        self.SetTitle(self._title)
        self.tc.SetValue(self._text)
        
    def kd(self, evt):
        if evt.GetKeyCode() ==ord("C") and evt.controlDown:
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(self._text))
                wx.TheClipboard.Close()
        elif evt.GetKeyCode()==ord("S") and evt.controlDown:
            import codecs
            with codecs.open(u".\\favorites\\%s.txt"%self._title, "w","utf-8") as f:
                f.write(self._text)
                wx.MessageBox(u"保存成功！", u"提示：")
        elif evt.GetKeyCode() in (8, 27):        # Keys:ESC and BACK
            self.Close()
        evt.Skip()
    
    def onclose(self, evt):
        self.Hide()  
        self.Parent.lc.SetFocus()

RE_LISTCONTENT=r'(?P<content><dl class="search-list.*?</dl>.*)+'
RE_LISTEXTRACT=r'<dd.*?<dt.*?<a.*?href="(?P<url>.*?)".*?>(?P<title>.*?)</a>'
RE_EM_TAG=r"(<em>)|(</em>)"

def parsehtmltolist(html):
    p_con=re.compile(RE_LISTCONTENT, flags=re.S)
    p_list=re.compile(RE_LISTEXTRACT, flags=re.S)
    p_em=re.compile(RE_EM_TAG)
    try:
        c=p_con.search(html).group("content")
        m=p_list.finditer(c)
        return [(p_em.sub("", n.group("title")), n.group("url")) for n in m]
    except Exception as e:
        print(str(e))
        return None
    
RETEXT_HtmlTag=r'<[^>]*?>'
RETEXT_StyleAndScript=r'(<style.*?>.*?</style>)|(<script.*?>.*?</script>)'
RETEXT_BlankLine=r'^\s*$'
RE_ARTICLECONTENT=r'<main>(?P<content>.*?)</main>'
    
def prettyhtml(html):
    p_content=re.compile(RE_ARTICLECONTENT, flags=re.S)
    p_htmltag=re.compile(RETEXT_HtmlTag,re.S)
    p_styleandscript=re.compile(RETEXT_StyleAndScript,re.S)
    p_blankline=re.compile(RETEXT_BlankLine)
    
    s=""
    try:
        s=p_content.search(html).group("content")

        p_head=re.compile(r"^.*?本文链接.*?(</a>)", re.S)
        p_tail=re.compile(r"展开阅读全文.*",re.S)
        s=p_head.sub("", s)
        s=p_tail.sub("", s)

        s=p_htmltag.sub("", p_styleandscript.sub("", s))

        lines=(p_blankline.sub("",line) for line in s.split("\n"))
        s="\r\n".join(i for i in lines if i)
        from html.parser import unescape
        s=unescape(s)
    except Exception as e:
        print(str(e))
    return s

class TheApp(wx.App):
    def OnInit (self):
        frame=MainFrame()
        self.SetTopWindow(frame)
        frame.Show()
        return True

def main():
    app=TheApp()
    app.MainLoop()

if __name__=="__main__":
    main()
        
