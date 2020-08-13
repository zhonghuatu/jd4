import requests
from bs4 import BeautifulSoup
from bson import objectid
import pymongo
import time
import tomd
import datetime
import json,random
import re,os
import http.cookiejar as cookielib
from requests.cookies import RequestsCookieJar
import configparser
import pymysql
import hashlib
from jd4 import recognize

HEADERS = {
    # User-Agent(UA) 服务器能够识别客户使用的操作系统及版本、CPU 类型、浏览器及版本、浏览器渲染引擎、浏览器语言、浏览器插件等。也就是说伪装成浏览器进行访问
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
    # 用于告诉服务器我是从哪个页面链接过来的，服务器基此可以获得一些信息用于处理。如果不加入，服务器可能依旧会判断为非法请求
    'Referer': 'http://ybt.ssoier.cn:8088'}

STATUS_ACCEPTED = 1
STATUS_WRONG_ANSWER = 2
STATUS_TIME_LIMIT_EXCEEDED = 3
STATUS_MEMORY_LIMIT_EXCEEDED = 4
STATUS_RUNTIME_ERROR = 6
STATUS_COMPILE_ERROR = 7
STATUS_SYSTEM_ERROR = 8
STATUS_JUDGING = 20
STATUS_COMPILING = 21

class YBTJudge:
    session = []
    username = []
    password = []
    useCookie = False
    now = 0
    tot = 0
    SLanguage = {"cc":1,"c":2,"java":3,"pas":4,"py":5,"py3":5}
    SResult = {
        "AC":STATUS_ACCEPTED,
        "PE":STATUS_WRONG_ANSWER,
        "WA":STATUS_WRONG_ANSWER,
        "OLE":STATUS_WRONG_ANSWER,
        "RE":STATUS_RUNTIME_ERROR,
        "TLE":STATUS_TIME_LIMIT_EXCEEDED,
        "MLE":STATUS_MEMORY_LIMIT_EXCEEDED,
        "CE":STATUS_COMPILE_ERROR,
        "RF":STATUS_SYSTEM_ERROR,
    }
    SResultTip = {
        "AC":"答案正确",
        "PE":"格式错误",
        "WA":"答案错误",
        "OLE":"输出超限",
        "RE":"运行错误",
        "TLE":"时间超限",
        "MLE":"空间超限",
        "CE":"编译错误",
        "RF":"权限错误",
    }
    
    def __init__(self, username, password, multi, uCookie):
        if multi:
            uname = username.split("|")
            pwd = password.split("|")
            if(len(uname)!=len(pwd)):
                raise AssertionError
            self.tot = len(uname)
        else:
            uname = [username]
            pwd = [password]
            self.tot = 1
        self.username = uname
        self.password = pwd
        self.useCookie = uCookie
        self.now = 0
        '''for i in range(0,self.tot):
            self.session.append(requests.Session())
            self.session[i].cookies = cookielib.LWPCookieJar(filename = "YBTcookies"+str(i)+".txt")
            try:
                self.session[i].cookies.load()
                for item in self.session[i].cookies:
                    print(item)'''
        for i in range(0,self.tot):
            self.session.append(requests.Session())
            try:
                config=configparser.ConfigParser()
                config.read("cookies/YBT.ini")
                f = json.loads(config.get(self.username[i],"contents"))
                print(self.csrf[i],self.bfaa[i],self.ftaa[i],self.tta[i])
                self.session[i].cookies=requests.utils.cookiejar_from_dict(f, cookiejar=None, overwrite=True)
            except:
                print(self.username[self.now] + " Cookie 未能加载")
        print("Init")

    def changeAccount(self):
        self.now += 1
        if self.now == self.tot:
            self.now = 0
        print("YBT Account changes into "+self.username[self.now])
    
    def CheckSession(self):
        print("Check Session For "+self.username[self.now])
        url = "http://ybt.ssoier.cn:8088"
        if(self.useCookie):
            Headers = HEADERS
            Headers['Cookie']=self.password[self.now]
            res = self.session[self.now].get(url, headers=Headers)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text,"lxml").find_all("th",width="15%")[1].contents[1]
            return soup.name=='table'
        else:
            res = self.session[self.now].get(url, headers=HEADERS)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text,"lxml").find_all("th",width="15%")[1].contents[1]
            return soup.name=='table'
    
    def Login(self):
        print(self.session[self.now].cookies)
        url = "http://ybt.ssoier.cn:8088/login.php"
        data={'username':self.username[self.now],'password':self.password[self.now],'login':'登录'}
        res = self.session[self.now].post(url,data=data,headers=HEADERS)
        res.encoding = 'utf-8'
        
        cookie=requests.utils.dict_from_cookiejar(res.cookies)
        config=configparser.ConfigParser()
        config.read("cookies/YBT.ini")
        try:
            config.add_section(self.username[self.now])
        except:
            pass
        config.set(self.username[self.now],"contents",json.dumps(cookie))
        config.write(open("cookies/YBT.ini", "w"))
        
    def Submit(self,pid,code,lang):
        data = {
            "user_id" : self.username[self.now],
            "problem_id" : pid,
            "language" : self.SLanguage[lang],
            "source" : code,
            "submit" : "提交"
        }
        print("submit")
        url = "http://ybt.ssoier.cn:8088/action.php"
        res = None
        if(self.useCookie):
            Headers = HEADERS
            Headers['Cookie']=self.password[self.now]
            res = self.session[self.now].post(url,data=data,headers=Headers)
        else:
            res = self.session[self.now].post(url,data=data,headers=HEADERS)
        res.encoding = 'utf-8'
        if res.text.find("提交频繁啦！")!=-1:
            return "-1"
        elif res.text.find("你的程序有被限制的函数,请检查你的代码。或你所在位置有无良访问。")!=-1:
            return "-3"
        else :
            try:
                print(BeautifulSoup("<a>"+res.text+"</a>","lxml"))
                return BeautifulSoup("<a>"+res.text+"</a>","lxml").script.string.replace("'","").split("=")[-1].replace(";","")
            except:
                print(res.text)
                time.sleep(5)
                print("Resubmitting...")
                last = self.now
                self.changeAccount()
                return self._Submit(pid,code,lang,last)
    
    def _Submit(self,pid,code,lang,last):
        if(last==self.now):
            return "-2"
        data = {
            "user_id" : self.username[self.now],
            "problem_id" : pid,
            "language" : self.SLanguage[lang],
            "source" : code,
            "submit" : "提交"
        }
        url = "http://ybt.ssoier.cn:8088/action.php"
        res = None
        if(self.useCookie):
            Headers = HEADERS
            Headers['Cookie']=self.password[self.now]
            res = self.session[self.now].post(url,data=data,headers=Headers)
        else:
            res = self.session[self.now].post(url,data=data,headers=HEADERS)
        res.encoding = 'utf-8'
        if res.text.find("提交频繁啦！")!=-1:
            return "-1"
        else :
            try:
                return BeautifulSoup("<a>"+res.text+"</a>","lxml").script.string.replace("'","").split("=")[-1].replace(";","")
            except:
                print(res.text)
                time.sleep(5)
                print("Resubmitting...")
                self.changeAccount()
                return self._Submit(pid,code,lang,last)
    
    def Monitor(self,rid,next,end):
        if rid == "index.php":
            end(status=STATUS_SYSTEM_ERROR,
                                 score=0,
                                 time_ms=0,
                                 memory_kb=0,
                                 judge_text="[SO SORRY that something unexpected happens]\nThis submission is posted to YBTOJ by "+self.username[self.now])
        url = "http://ybt.ssoier.cn:8088/statusx1.php?runidx="+rid
        print(url)
        res = None
        if(self.useCookie):
            Headers = HEADERS
            Headers['Cookie']=self.password[self.now]
            res = self.session[self.now].get(url,headers=Headers)
        else:
            res = self.session[self.now].get(url,headers=HEADERS)
        res.encoding = 'utf-8'
        staText = res.text.split(":")
        while staText[4] == "Waiting" or staText[4] == "Judging":
            if staText[4] == "Waiting":
                next(status=STATUS_COMPILING, progress=0)
            else:
                next(status=STATUS_JUDGING, progress=0)
            time.sleep(1)
            res = None
            if(self.useCookie):
                Headers = HEADERS
                Headers['Cookie']=self.password[self.now]
                res = self.session[self.now].get(url,headers=Headers)
            else:
                res = self.session[self.now].get(url,headers=HEADERS)
            res.encoding = 'utf-8'
            staText = res.text.split(":")
        if staText[4] == "Compile Error":
            url = "http://ybt.ssoier.cn:8088/show_ce_info.php?runid="+rid
            res = None
            if(self.useCookie):
                Headers = HEADERS
                Headers['Cookie']=self.password[self.now]
                res = self.session[self.now].get(url,headers=Headers)
            else:
                res = self.session[self.now].get(url,headers=HEADERS)
            res.encoding = 'utf-8'
            soup = str(BeautifulSoup(res.text,"lxml").find("td",attrs={"class":"ceinfo"})).replace('<td class="ceinfo">','').replace('</td>','').replace('\n','').replace('<br/>','\n').replace('\n\n','\n')
            next(compiler_text=soup)
            end(status=STATUS_COMPILE_ERROR,
                 score=0,
                 time_ms=0,
                 memory_kb=0)
            return
        staText[4] = staText[4].split("|")
        staText[5] = staText[5].split(",")
        total_time_usage_ms = 0
        total_memory_usage_kb = 0
        total_score = 0
        total_status = STATUS_WRONG_ANSWER
        if staText[4][0]=="Accepted":
            total_score = 100
            total_status = STATUS_ACCEPTED
        for i in range(0,len(staText[5])):
            if staText[5][i]=="": continue
            staText[5][i] = staText[5][i].split("|")
            if staText[5][i][0]=="AC":
                score = 100//(len(staText[5])-1)
                total_score += score
            else:
                score = 0
            staText[5][i][1] = staText[5][i][1].split("_")
            total_memory_usage_kb += int(staText[5][i][1][0])
            total_time_usage_ms += int(staText[5][i][1][1])
            next(status=STATUS_JUDGING,
                      case={
                            'status': self.SResult[staText[5][i][0]],
                            'score': score,
                            'time_ms': int(staText[5][i][1][1]),
                            'memory_kb': int(staText[5][i][1][0]),
                            'judge_text': self.SResultTip[staText[5][i][0]]+"    ["+str(score)+"]"},
                      progress=99)
        if staText[4][0]=="Accepted":
            total_score = 100
            total_status = STATUS_ACCEPTED
        end(status=total_status,
                 score=total_score,
                 time_ms=total_time_usage_ms,
                 memory_kb=total_memory_usage_kb,
                 judge_text="This submission is posted to YBTOJ by "+self.username[self.now])

class BZOJJudge:
    session = []
    username = []
    password = []
    now = 0
    tot = 0
    SLanguage = {"cc":1,"c":2,"java":3,"pas":4,"py":5,"py3":5}
    SResult = {
        "Accepted":STATUS_ACCEPTED,
        "Presentation_Error":STATUS_WRONG_ANSWER,
        "Wrong_Answer":STATUS_WRONG_ANSWER,
        "Output_Limit_Exceed":STATUS_WRONG_ANSWER,
        "Runtime_Error":STATUS_RUNTIME_ERROR,
        "Time_Limit_Exceed":STATUS_TIME_LIMIT_EXCEEDED,
        "Memory_Limit_Exceed":STATUS_MEMORY_LIMIT_EXCEEDED,
        "Compile Error":STATUS_COMPILE_ERROR
    }
    
    def __init__(self, username, password, multi):
        if multi:
            uname = username.split("|")
            pwd = password.split("|")
            if(len(uname)!=len(pwd)):
                raise AssertionError
            self.tot = len(uname)
        else:
            uname = [username]
            pwd = [password]
            self.tot = 1
        self.username = uname
        self.password = pwd
        self.now = 0
        for i in range(0,self.tot):
            self.session.append(requests.Session())
            self.session[i].cookies = cookielib.LWPCookieJar(filename = "BZOJcookies"+str(i)+".txt")
            try:
                self.session[i].cookies.load()
                for item in self.session[i].cookies:
                    print(item)
            except:
                print(str(i) + " Cookie 未能加载")
        print("Init")
    

    def changeAccount(self):
        self.now += 1
        if self.now == self.tot:
            self.now = 0
        print("BZOI Account changes into "+self.username[self.now])
        
    def CheckSession(self):
        url = "https://www.lydsy.com/JudgeOnline/submitpage.php?id=1001"
        res = self.session[self.now].get(url, headers=HEADERS)
        res.encoding = 'utf-8'
        ss = res.text
        return ss.find("Login")==-1
    
    def Login(self):
        url = "https://www.lydsy.com/JudgeOnline/login.php"
        data={'user_id':self.username[self.now],'password':self.password[self.now],'submit':'Submit'}
        res = self.session[self.now].post(url,data=data,headers=HEADERS)
        res.encoding = 'utf-8'
        print(res.text)
        self.session[self.now].cookies.save()
    
    def Submit(self,pid,code,lang):
        data = {
            "id" : pid,
            "language" : self.SLanguage[lang],
            "source" : code,
        }
        url = "https://www.lydsy.com/JudgeOnline/submit.php"
        res = self.session[self.now].post(url,data=data,headers=HEADERS)
        res.encoding = 'utf-8'
        if res.text.find("You should not submit more than twice in 10 seconds.....")!=-1:
            return "-1"
        else :
            try:
                return BeautifulSoup(res.text,"lxml").find("table",align="center").find("tr",align="center").td.string
            except:
                time.sleep(5)
                last = self.now
                self.changeAccount()
                print("Resubmitting...")
                return self._Submit(pid,code,lang,last)

    def _Submit(self,pid,code,lang,last):
        if(self.now==last):
            return "-2"
        data = {
            "id" : pid,
            "language" : self.SLanguage[lang],
            "source" : code,
        }
        url = "https://www.lydsy.com/JudgeOnline/submit.php"
        res = self.session[self.now].post(url,data=data,headers=HEADERS)
        res.encoding = 'utf-8'
        if res.text.find("You should not submit more than twice in 10 seconds.....")!=-1:
            return "-1"
        else :
            try:
                return BeautifulSoup(res.text,"lxml").find("table",align="center").find("tr",align="center").td.string
            except:
                time.sleep(5)
                self.changeAccount()
                print("Resubmitting...")
                return self._Submit(pid,code,lang,last)
    
    def Monitor(self,pid,rid,next,end):
        url = "https://www.lydsy.com/JudgeOnline/status.php?problem_id="+pid+"&user_id="+self.username[self.now]
        res = self.session[self.now].get(url,headers=HEADERS)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text,"lxml").find("table",align="center").find_all("tr",align="center")
        for soup1 in soup:
            if soup1.td.string != rid:
                continue
            soup2 = soup1
            break
        soup1 = soup2.find_all("td")
        while soup1[3].string.find("Pending") != -1 or soup1[3].string.find("Judging") != -1 or soup1[3].string.find("Compiling") != -1:
            if soup1[3].string.find("Judging") != -1:
                next(status=STATUS_JUDGING, progress=0)
            else:
                next(status=STATUS_COMPILING, progress=0)
            time.sleep(1)
            res = self.session[self.now].get(url,headers=HEADERS)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text,"lxml").find("table",align="center").find_all("tr",align="center")
            for soup1 in soup:
                if soup1.td.string != rid:
                    continue
                soup2 = soup1
                break
            soup1 = soup2.find_all("td")
            
        if soup1[3].string == "Compile_Error":
            url = "https://www.lydsy.com/JudgeOnline/ceinfo.php?sid="+rid
            res = self.session[self.now].get(url,headers=HEADERS)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text,"lxml").find("pre").string
            next(compiler_text=soup)
            end(status=STATUS_COMPILE_ERROR,
                 score=0,
                 time_ms=0,
                 memory_kb=0)
            return
        score = 0
        if soup1[3].string == "Accepted":
            score = 100
        next(status=STATUS_JUDGING,
              case={
                    'status': self.SResult[soup1[3].string],
                    'score': score,
                    'time_ms': int(soup1[5].contents[0].string),
                    'memory_kb': int(soup1[4].contents[0].string),
                    'judge_text': soup1[3].string},
              progress=99)
        end(status=self.SResult[soup1[3].string],
                 score=score,
                 time_ms=int(soup1[5].contents[0].string),
                 memory_kb=int(soup1[4].contents[0].string),
                 judge_text="This submission is posted to BZOJ by "+self.username[self.now])

class XJOIJudge:
    session = []
    username = []
    password = []
    now = 0
    tot = 0
    SLanguage = {"cc":"g++","c":"gcc","pas":"fps"}
    SResult = {
        "Accepted":STATUS_ACCEPTED,
        "Wrong Answer":STATUS_WRONG_ANSWER,
        "Runtime Error":STATUS_RUNTIME_ERROR,
        "Time Limit Exceeded":STATUS_TIME_LIMIT_EXCEEDED,
        "Memory Limit Exceeded":STATUS_MEMORY_LIMIT_EXCEEDED,
        "Compile Error":STATUS_COMPILE_ERROR,
        "Dangerous Syscall":STATUS_RUNTIME_ERROR,
        "Running":STATUS_JUDGING
    }
    
    def __init__(self, username, password, multi):
        if multi:
            uname = username.split("|")
            pwd = password.split("|")
            if(len(uname)!=len(pwd)):
                raise AssertionError
            self.tot = len(uname)
        else:
            uname = [username]
            pwd = [password]
            self.tot = 1
        self.username = uname
        self.password = pwd
        self.now = 0
        '''for i in range(0,self.tot):
            self.session.append(requests.Session())
            self.session[i].cookies = cookielib.LWPCookieJar(filename = "XJOIcookies"+str(i)+".txt")
            try:
                self.session[i].cookies.load()
                for item in self.session[i].cookies:
                    print(item)'''
        for i in range(0,self.tot):
            self.session.append(requests.Session())
            try:
                config=configparser.ConfigParser()
                config.read("cookies/XJOI.ini")
                f = json.loads(config.get(self.username[i],"contents"))
                print(self.csrf[i],self.bfaa[i],self.ftaa[i],self.tta[i])
                self.session[i].cookies=requests.utils.cookiejar_from_dict(f, cookiejar=None, overwrite=True)
            except:
                print(str(i) + " Cookie 未能加载")
        print("Init")
    

    def changeAccount(self):
        self.now += 1
        if self.now == self.tot:
            self.now = 0
        print("XJOI Account changes into "+self.username[self.now])
        
    def CheckSession(self):
        url = "http://115.236.49.52:83/problem/1000"
        res = self.session[self.now].get(url, headers=HEADERS)
        res.encoding = 'utf-8'
        ss = res.text
        return ss.find("Access Denied")==-1
    
    def Login(self):
        url = "http://115.236.49.52:83"
        res = self.session[self.now].get(url,headers=HEADERS)
        res.encoding = 'utf-8'
        clientId = re.search(r'https://id.xjoi.net/login\?clientId=[^\s]*', res.text, re.M|re.I).group()[-11:-2]
        url = "https://id.xjoi.net/api/login"
        data= '{"username":"'+self.username[self.now]+'","password":"'+self.password[self.now]+'","remember":true}'
        res = self.session[self.now].post(url,data=data,headers={"Content-Type":"application/json;charset=utf-8"})
        res.encoding = 'utf-8'
        print(res.text)
        url = "https://id.xjoi.net/api/oauth/redirect-callback?clientId="+clientId
        res = self.session[self.now].get(url,headers=HEADERS)
        res.encoding = 'utf-8'
        url = "https://dev.xjoi.net/api/oauth/callback"
        res = self.session[self.now].get(url,headers=HEADERS)
        res.encoding = 'utf-8'
        
        cookie=requests.utils.dict_from_cookiejar(res.cookies)
        config=configparser.ConfigParser()
        config.read("cookies/XJOI.ini")
        try:
            config.add_section(self.username[self.now])
        except:
            pass
        config.set(self.username[self.now],"contents",json.dumps(cookie))
        config.write(open("cookies/XJOI.ini", "w"))
    
    def Submit(self,pid,code,lang):
        data = {
            "proid" : pid,
            "language" : self.SLanguage[lang],
            "source" : code,
        }
        url = "http://115.236.49.52:83/submit"
        res = self.session[self.now].post(url,data=data,headers=HEADERS)
        res.encoding = 'utf-8'
        print(res.text)
        if res.text.find("请稍后再提交")!=-1:
            return "-1"
        elif res.text.find("Access Denied")!=-1:
            return "-3"
        else :
            try:
                url = "http://115.236.49.52:83/status?pid="+pid+"&user="+self.username[self.now]+"&status=All&language="+self.SLanguage[lang]
                res = self.session[self.now].get(url, headers=HEADERS)
                res.encoding = 'utf-8'
                return BeautifulSoup(res.text,"lxml").find("a",attrs = {"class":"status-table-text"}).string.replace(" ","")
            except:
                time.sleep(10)
                print("Resubmitting...")
                return self.Submit(pid,code,lang)
    
    def Monitor(self,rid,next,end):
        url = "http://115.236.49.52:83/detail/"+rid
        res = self.session[self.now].get(url,headers=HEADERS)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text,"lxml").find("textarea",readonly="readonly").string
        flag = False
        last = 0
        if(soup == None or soup.replace(" ","")==""):
            flag = True
        else:
            soup = soup.split("\n")
            while(soup.count("")):
                soup.remove("")
            if soup[1].split(" ")[-1]=="Running":
                flag = True
        while flag:
            flag = False
            if(soup == None):
                time.sleep(0.1)
            elif soup[1].split(" ")[-1]=="Running":
                if(last<len(soup)-2):
                    for i in range(2+last,len(soup)):
                        soup[i] = soup[i].split(": ")
                        if(soup[i][-1]=="Running"):
                            flag=True
                            break
                        last+=1
                        next(status=STATUS_JUDGING,
                            case={
                                'status': self.SResult[soup[i][-1]],
                                'score': int(soup[i][4][0:-8]),
                                'time_ms': int(soup[i][2][0:-10]),
                                'memory_kb': int(soup[i][3][0:-10]),
                                'judge_text': soup[i][-1]+"["+soup[i][4][0:-8]+"]"},
                            progress=len(soup)-2)
            else:
                next(status=STATUS_COMPILING, progress=0)
            time.sleep(1)
            res = self.session[self.now].get(url,headers=HEADERS)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text,"lxml").find("textarea",readonly="readonly").string
            if(soup == None or soup==""):
                flag = True
            else:
                soup = soup.split("\n")
                while(soup.count("")):
                    soup.remove("")
                if soup[1].split(" ")[-1]=="Running":
                    flag = True
            
        if soup[0] == "compile error:":
            next(compiler_text="\n".join(soup[1:-1]))
            end(status=STATUS_COMPILE_ERROR,
                 score=0,
                 time_ms=0,
                 memory_kb=0)
            return
        res = self.session[self.now].get(url,headers=HEADERS)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text,"lxml").find("textarea",readonly="readonly").string
        soup = soup.split("\n")
        while(soup.count("")):
            soup.remove("")
        if(last<len(soup)-2):
            for i in range(2+last,len(soup)):
                soup[i] = soup[i].split(": ")
                next(status=STATUS_JUDGING,
                    case={
                        'status': self.SResult[soup[i][-1]],
                        'score': int(soup[i][4][0:-8]),
                        'time_ms': int(soup[i][2][0:-10]),
                        'memory_kb': int(soup[i][3][0:-10]),
                        'judge_text': soup[i][-1]+"["+soup[i][4][0:-8]+"]"},
                    progress=len(soup)-2)
            last = len(soup)-2
        soup[1] = soup[1].split(": ")
        end(status=self.SResult[soup[1][-1]],
                 score=int(soup[1][3][0:-8]),
                 time_ms=int(soup[1][1][0:-10]),
                 memory_kb=int(soup[1][2][0:-9]))

class HUSTJudge:
    BASE_OJ = "HUSTDemo"
    SHOW_OJ = "HUSTDemo"
    BASE_URL = "http://demo.hustoj.com"
    SHOW_RE = True
    session = []
    username = []
    password = []
    now = 0
    tot = 0
    vcode = False
    SLanguage = {
        "pas"  :2,
        "cc"   :1,
        "c"    :0,
        "java" :3,
        "py"   :6,
        "cs"   :9,
        "php"  :7,
        "go"   :17,
        "js"   :16,
        "rb"   :4
    }
    SResult = {
        "Accepted":STATUS_ACCEPTED,
        "Presentation Error":STATUS_WRONG_ANSWER,
        "Wrong Answer":STATUS_WRONG_ANSWER,
        "Output Limit Exceeded":STATUS_WRONG_ANSWER,
        "Runtime Error":STATUS_RUNTIME_ERROR,
        "Time Limit Exceeded":STATUS_TIME_LIMIT_EXCEEDED,
        "Memory Limit Exceeded":STATUS_MEMORY_LIMIT_EXCEEDED,
        "Compile Error":STATUS_COMPILE_ERROR,
        "Running":STATUS_JUDGING
    }
    SResult1 = [
        STATUS_COMPILING,STATUS_COMPILING,STATUS_COMPILING,STATUS_JUDGING,STATUS_ACCEPTED,
        STATUS_WRONG_ANSWER,STATUS_WRONG_ANSWER,STATUS_TIME_LIMIT_EXCEEDED,STATUS_MEMORY_LIMIT_EXCEEDED,STATUS_WRONG_ANSWER,
        STATUS_RUNTIME_ERROR,STATUS_COMPILE_ERROR,STATUS_COMPILING,STATUS_JUDGING
    ]
    HEADERS = {}
    def __init__(self, username, password, multi):
        if multi:
            uname = username.split("|")
            pwd = password.split("|")
            if(len(uname)!=len(pwd)):
                raise AssertionError
            self.tot = len(uname)
        else:
            uname = [username]
            pwd = [password]
            self.tot = 1
        self.username = uname
        self.password = pwd
        self.now = random.randint(0,len(self.username)-1)
        self.HEADERS = {
            # User-Agent(UA) 服务器能够识别客户使用的操作系统及版本、CPU 类型、浏览器及版本、浏览器渲染引擎、浏览器语言、浏览器插件等。也就是说伪装成浏览器进行访问
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
            # 用于告诉服务器我是从哪个页面链接过来的，服务器基此可以获得一些信息用于处理。如果不加入，服务器可能依旧会判断为非法请求
            'Referer': self.BASE_URL,
            'Host': self.BASE_URL.replace("http://","").replace("https://","")
        }
        
        """for i in range(0,self.tot):
            self.session.append(requests.Session())
            self.session[i].cookies = cookielib.LWPCookieJar(filename = "XJOIcookies"+str(i)+".txt")
            try:
                self.session[i].cookies.load()
                for item in self.session[i].cookies:
                    print(item)"""
        for i in range(0,self.tot):
            self.session.append(requests.Session())
            try:
                config=configparser.ConfigParser()
                config.read("cookies/"+self.BASE_OJ+".ini")
                f = json.loads(config.get(self.username[i],"contents"))
                print(self.csrf[i],self.bfaa[i],self.ftaa[i],self.tta[i])
                self.session[i].cookies=requests.utils.cookiejar_from_dict(f, cookiejar=None, overwrite=True)
            except:
                print(str(i) + " Cookie 未能加载")
        print("Init")
    
    def __vcode(self):
        url = self.BASE_URL + "/vcode.php"
        res = self.session[self.now].get(url,headers=self.HEADERS)
        #data["vcode"] = recognize.recog(Bytes2Data(res.content))
        path = "vcode/vcode-"+str(time.time())+".gif"
        with open(path,"wb") as f:
            f.write(res.content)
            f.close()
        res = recognize.recog(path)
        res = res.replace(".","").replace("-","").replace("*","").replace(":","")
        print(path,res)
        while ((not res.isdigit()) or len(res)!=4):
            os.remove(path)
            time.sleep(1)
            url = self.BASE_URL + "/vcode.php"
            res = self.session[self.now].get(url,headers=self.HEADERS)
            #data["vcode"] = recognize.recog(Bytes2Data(res.content))
            path = "vcode/vcode-"+str(time.time())+".gif"
            with open(path,"wb") as f:
                f.write(res.content)
                f.close()
            res = recognize.recog(path)
            res = res.replace(".","").replace("-","").replace("*","").replace(":","")
            print(path,res)
        return res
    
    def changeAccount(self):
        self.now += 1
        if self.now == self.tot:
            self.now = 0
        print(self.BASE_OJ+"(HUST) Account changes into "+self.username[self.now])
        
    def CheckSession(self):
        url = self.BASE_URL + "/submitpage.php?id=1000"
        res = self.session[self.now].get(url, headers=self.HEADERS)
        res.encoding = 'utf-8'
        ss = res.text
        print(ss.find('loginpage.php'))
        return ss.find('loginpage.php')==-1
    
    def Login(self):
        url = self.BASE_URL + "/csrf.php"
        res = self.session[self.now].get(url,headers=self.HEADERS)
        res.encoding = 'utf-8'
        
        #print(res.text)
        csrf = BeautifulSoup(res.text,"lxml").find("input",attrs={"name":"csrf"})["value"]
        
        data = {
            "csrf"    : csrf,
            "submit"  : "",
            "user_id": self.username[self.now],
            "password": self.password[self.now]
        }
        
        if(self.vcode):
            data["vcode"] = self.__vcode()
        
        url = self.BASE_URL + "/login.php"
        res = self.session[self.now].post(url,headers=self.HEADERS,data=data)
        res.encoding = 'utf-8'
        if res.text.find("history.go(-2);")!=-1:
            print("Succeed in logining",self.BASE_OJ)
        else:
            print(re.search(r"alert\('(.+?)'\)", res.text, re.M|re.I).group()[7:-3])
        
        cookie=requests.utils.dict_from_cookiejar(res.cookies)
        config=configparser.ConfigParser()
        config.read("cookies/"+self.BASE_OJ+".ini")
        try:
            config.add_section(self.username[self.now])
        except:
            pass
        config.set(self.username[self.now],"contents",json.dumps(cookie))
        config.write(open("cookies/"+self.BASE_OJ+".ini", "w"))
    
    def Submit(self,pid,code,lang):
        url = self.BASE_URL + "/csrf.php"
        res = self.session[self.now].get(url,headers=self.HEADERS)
        res.encoding = 'utf-8'
        
        #print(res.text)
        csrf = BeautifulSoup(res.text,"lxml").find("input",attrs={"name":"csrf"})["value"]
        
        data = {
            "id"      : pid,
            "language": self.SLanguage[lang],
            "source"  : code,
            "csrf"    : csrf
        }
        
        if(self.vcode):
            data["vcode"] = self.__vcode()
        
        url = self.BASE_URL + "/submit.php"
        res = self.session[self.now].post(url,data=data)
        res.encoding = 'utf-8'
        #print(res.text)
        if(res.text.find("提交超过")!=-1):
            return "-1"
        elif(res.text.find("Verification Code Wrong!")!=-1):
            return "-3"
        try:
            return BeautifulSoup(res.text,"lxml").find("table",attrs={"id":"result-tab"}).tbody.tr.td.string
        except:
            print(res.text,BeautifulSoup(res.text,"lxml").find("table",attrs={"id":"result-tab"}))
            return "-2"
    
    def Monitor(self,rid,next,end):
        print(rid)
        url = self.BASE_URL + "/status-ajax.php?solution_id="+rid
        res = self.session[self.now].get(url,headers=self.HEADERS)
        res.encoding = 'utf-8'
        ress = res.text.split(",")
        #print(res.text)
        
        while self.SResult1[int(ress[0])]==STATUS_COMPILING or self.SResult1[int(ress[0])]==STATUS_JUDGING:
            next(status=self.SResult1[int(ress[0])], progress=0)
            time.sleep(1)
            url = self.BASE_URL + "/status-ajax.php?solution_id="+rid
            res = self.session[self.now].get(url,headers=self.HEADERS)
            res.encoding = 'utf-8'
            ress = res.text.split(",")
        
        next(status=STATUS_JUDGING, progress=75)
        
        if self.SResult1[int(ress[0])]==STATUS_COMPILING == STATUS_COMPILE_ERROR:
            url = self.BASE_URL + "/ceinfo.php?sid="+rid
            res = self.session[self.now].get(url,headers=self.HEADERS)
            res.encoding = 'utf-8'
            next(compiler_text=str(soup.find("pre",attrs={"id":"errtxt"}).string))
            end(status=STATUS_COMPILE_ERROR,
                 score=0,
                 time_ms=0,
                 memory_kb=0)
            return
        
        if(len(ress)>=5):
            score = str(ress[4])
        elif self.SResult1[int(ress[0])]==STATUS_ACCEPTED:
            score = 100
        else:
            score = 0
        
        if self.SHOW_RE:
            url = self.BASE_URL + "/reinfo.php?sid="+rid
            res = self.session[self.now].get(url,headers=self.HEADERS)
            res.encoding = 'utf-8'
            watext = "\n---------------OJ Returns---------------n" + str(soup.find("pre",attrs={"id":"errtxt"}).string)
        else:
            watext = ""
        
        watext = "This submission is posted to " + self.SHOW_OJ + "(HUST) by " + self.username[self.now] + watext
        
        next(status=STATUS_JUDGING,
                case={
                    'status': self.SResult1[int(ress[0])],
                    'score': score,
                    'time_ms': int(ress[2].replace(" ms","")),
                    'memory_kb': int(ress[1].replace(" KB","")),
                    'judge_text': ""},
                progress=99)
        
        end(status=self.SResult1[int(ress[0])],
                 score=score,
                 time_ms=int(ress[2].replace(" ms","")),
                 memory_kb=int(ress[1].replace(" KB","")),
                 judge_text=watext)

class TKJudge(HUSTJudge):
    BASE_OJ = "TK"
    SHOW_OJ = ""
    BASE_URL = "http://tk.hustoj.com"
    vcode = True
    SHOW_RE = False

class UOJJudge:
    BASE_OJ = "UOJ"
    BASE_URL = "http://uoj.ac"
    session = []
    username = []
    password = []
    now = 0
    tot = 0
    HEADERS = {}
    SLanguage = {
        "pas":"Pascal",
        "cc":"C++",
        "c":"C",
        "java":"Java7",
        "py":"Python2.7",
        "py3":"Python3",
        "cs":"C++11",
        "js":"Java8",
    }
    SResult = {
        "Accepted":STATUS_ACCEPTED,
        "Wrong Answer":STATUS_WRONG_ANSWER,
        "Runtime Error":STATUS_RUNTIME_ERROR,
        "Time Limit Exceeded":STATUS_TIME_LIMIT_EXCEEDED,
        "Memory Limit Exceeded":STATUS_MEMORY_LIMIT_EXCEEDED,
        "Compile Error":STATUS_COMPILE_ERROR,
        "Dangerous Syscall":STATUS_RUNTIME_ERROR,
        "Running":STATUS_JUDGING
    }
    
    def __init__(self, username, password, multi):
        if multi:
            uname = username.split("|")
            pwd = password.split("|")
            if(len(uname)!=len(pwd)):
                raise AssertionError
            self.tot = len(uname)
        else:
            uname = [username]
            pwd = [password]
            self.tot = 1
        self.username = uname
        self.password = pwd
        self.now = 0
        self.HEADERS = {
            # User-Agent(UA) 服务器能够识别客户使用的操作系统及版本、CPU 类型、浏览器及版本、浏览器渲染引擎、浏览器语言、浏览器插件等。也就是说伪装成浏览器进行访问
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
            # 用于告诉服务器我是从哪个页面链接过来的，服务器基此可以获得一些信息用于处理。如果不加入，服务器可能依旧会判断为非法请求
            'Referer': self.BASE_URL + "/submission",
            'Host': self.BASE_URL.replace("http://","").replace("https://","")
        }
        
        """for i in range(0,self.tot):
            self.session.append(requests.Session())
            self.session[i].cookies = cookielib.LWPCookieJar(filename = "XJOIcookies"+str(i)+".txt")
            try:
                self.session[i].cookies.load()
                for item in self.session[i].cookies:
                    print(item)"""
        for i in range(0,self.tot):
            self.session.append(requests.Session())
            try:
                config=configparser.ConfigParser()
                config.read("cookies/"+self.BASE_OJ+".ini")
                f = json.loads(config.get(self.username[i],"contents"))
                print(self.csrf[i],self.bfaa[i],self.ftaa[i],self.tta[i])
                self.session[i].cookies=requests.utils.cookiejar_from_dict(f, cookiejar=None, overwrite=True)
            except:
                print(str(i) + " Cookie 未能加载")
        print("Init")
    
    def changeAccount(self):
        self.now += 1
        if self.now == self.tot:
            self.now = 0
        print(self.BASE_OJ+"(UOJ) Account changes into "+self.username[self.now])
        
    def CheckSession(self):
        url = self.BASE_URL
        res = self.session[self.now].get(url, headers=self.HEADERS)
        res.encoding = 'utf-8'
        ss = res.text
        return ss.find(self.BASE_URL+"/login")==-1
    
    def Login(self):
        url = self.BASE_URL + "/login"
        res = self.session[self.now].get(url,headers=self.HEADERS)
        res.encoding = 'utf-8'
        
        token = re.search(r'_token : "(.+?)"', res.text, re.M|re.I).group()[10:70]
        #print("token:",token,"(",len(token),")")
        #salt = bytes(re.search(r'val\(\), "(.+?)"', res.text, re.M|re.I).group()[8:-1], encoding='utf-8')
        #obj=hashlib.md5(salt)
        #obj.update(self.password[self.now].encode('utf-8'))
        #pwd = str(obj.hexdigest())
        pwd = self.password[self.now]
        
        #with open("web.html","w") as f:
        #    f.write(res.text + "\n\ntoken : " + token + "\nsalt  : " + re.search(r'val\(\), "(.+?)"', res.text, re.M|re.I).group()[8:-1])
        
        data = {
            "_token"  : token,
            "login"   : "",
            "username": self.username[self.now],
            "password": pwd
        }
        print(data)
        res = self.session[self.now].post(url,headers=self.HEADERS,data=data)
        
        cookie=requests.utils.dict_from_cookiejar(res.cookies)
        config=configparser.ConfigParser()
        config.read("cookies/"+self.BASE_OJ+".ini")
        try:
            config.add_section(self.username[self.now])
        except:
            pass
        config.set(self.username[self.now],"contents",json.dumps(cookie))
        config.write(open("cookies/"+self.BASE_OJ+".ini", "w"))
    
    def Submit(self,pid,code,lang):
        url = self.BASE_URL + "/problem/"+str(pid)
        res = self.session[self.now].get(url,headers=self.HEADERS)
        res.encoding = 'utf-8'
        token = BeautifulSoup(res.text,"lxml").find_all("input",attrs = {"name":"_token"})[0]['value']
        data = """-----------------------------2341433157197025002472170340
Content-Disposition: form-data; name="_token"

{0}
-----------------------------2341433157197025002472170340
Content-Disposition: form-data; name="answer_answer_language"

{1}
-----------------------------2341433157197025002472170340
Content-Disposition: form-data; name="answer_answer_upload_type"

editor
-----------------------------2341433157197025002472170340
Content-Disposition: form-data; name="answer_answer_editor"

{2}
-----------------------------2341433157197025002472170340
Content-Disposition: form-data; name="answer_answer_file"; filename=""
Content-Type: application/octet-stream


-----------------------------2341433157197025002472170340
Content-Disposition: form-data; name="submit-answer"

answer
-----------------------------2341433157197025002472170340--
""".format(token,self.SLanguage[lang],code)
        hder = {
            # User-Agent(UA) 服务器能够识别客户使用的操作系统及版本、CPU 类型、浏览器及版本、浏览器渲染引擎、浏览器语言、浏览器插件等。也就是说伪装成浏览器进行访问
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
            # 用于告诉服务器我是从哪个页面链接过来的，服务器基此可以获得一些信息用于处理。如果不加入，服务器可能依旧会判断为非法请求
            'Referer': self.BASE_URL + "/submission" ,
            'Host': self.BASE_URL.replace("http://","").replace("https://","") ,
            'Content-Type': "multipart/form-data; boundary=---------------------------2341433157197025002472170340",
            'Content-Length':str(len(data))
        }
        res = self.session[self.now].post(url,data=data,headers=hder)
        res.encoding = 'utf-8'
        #print(res.text)
        return re.search(r'update_judgement_status_details\((.+?)\)', res.text, re.M|re.I).group()[32:-1]
    
    def Monitor(self,rid,next,end):
        print(rid)
        url = self.BASE_URL + "/submission-status-details?get%5B%5D="+rid
        res = None
        sta = None
        try:
            res = self.session[self.now].get(url,headers=self.HEADERS)
            res.encoding = 'utf-8'
            #print(res.text)
            res = json.loads(res.text.replace("\\n",""))
            #<td colspan="233" style="vertical-align: middle"><div class="uoj-status-details-img-div"><img src="http://img.uoj.ac/utility/bear-flying.gif" alt="小熊像超人一样飞" class="img-rounded" /></div><div class="uoj-status-details-text-div">Compiling</div></td>
            #sta = BeautifulSoup(res["html"],"lxml").find("div",attrs={"class":"uoj-status-details-text-div"}).string
            res = res[0]
            #print(res)
            sta = re.search(r'<div class="uoj-status-details-text-div">(.+?)</div>', res["html"], re.M|re.I).group()[41:-6]
            print(sta)
        except:
            res = {"judged":True}
        
        while res["judged"]==False:
            flag = False
            if (sta == "Judging"):
                next(status=STATUS_JUDGING, progress=0)
            else:
                next(status=STATUS_COMPILING, progress=0)
            time.sleep(1)
            try:
                res = self.session[self.now].get(url,headers=self.HEADERS)
                res.encoding = 'utf-8'
                res = json.loads(res.text.replace("\\n",""))
                res = res[0]
                sta = re.search(r'<div class="uoj-status-details-text-div">(.+?)</div>', res["html"], re.M|re.I).group()[41:-6]
                print(sta)
            except:
                print(res)
                res = {"judged":True}
            
            #sta = BeautifulSoup(res["html"],"lxml").find("div",attrs={"class":"uoj-status-details-text-div"}).string
        print(sta)
        url = self.BASE_URL + "/submission/"+rid
        print(self.HEADERS)
        
        FLAG = True
        cnt = 0
        while FLAG and cnt < 10:
            try:
                res = self.session[self.now].get(url,headers=self.HEADERS)
            except:
                print("Failed in try {} ,will retry after 1 seconds.".format(cnt))
                time.sleep(1)
                cnt+=1
            else:
                print("Succeed.")
                FLAG = False
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text,"lxml")
        
        #with open("web.html","w") as f:
        #    f.write(res.text)
        #with open("web.html","r") as f:
        #    soup = BeautifulSoup(f.read(),"lxml")
        
        next(status=STATUS_JUDGING, progress=0)
        
        #print(soup.find("table",attrs={"class":"table table-bordered table-text-center"}).tbody.find_all("td"))
        fscore = soup.find("table",attrs={"class":"table table-bordered table-text-center"}).tbody.tr.find_all("td")[3].a.string
        ftime = soup.find("table",attrs={"class":"table table-bordered table-text-center"}).tbody.tr.find_all("td")[4].string[0:-2]
        fmemory = soup.find("table",attrs={"class":"table table-bordered table-text-center"}).tbody.tr.find_all("td")[5].string[0:-2]
        
        if fscore == "Compile Error":
            next(compiler_text=str(soup.find_all("div",attrs={"class":"panel panel-info"})[1].find("pre")))
            end(status=STATUS_COMPILE_ERROR,
                 score=0,
                 time_ms=0,
                 memory_kb=0)
            return
        
        watext = ""
        cnt = 0
        finalStatus = 0
        #print(soup.find("div",attrs={"id":"details_details_accordion"}).contents)
        
        for soup2 in soup.find("div",attrs={"id":"details_details_accordion"}).contents:
            
            try:
                tmp = soup2["class"]
            except:
                #print("Shit")
                continue
            
            if ("text-right" in soup2["class"]):
                #print(soup2["class"],"Fuck")
                continue
            else:
                #print(cnt)
                cnt += 1
                #print(soup2)
                soup1 = soup2.contents[0].div.contents
                if self.SResult[soup1[2].string] == STATUS_WRONG_ANSWER:
                    watext = watext + "---------------------------------\n" 
                    watext = watext + soup1[0].h4.string 
                    watext = watext + "\n Input : \n" + soup2.contents[1].div.contents[2].string
                    watext = watext + "\n Output : \n" + soup2.contents[1].div.contents[5].string
                    watext = watext + "\n Result : \n" + soup2.contents[1].div.contents[8].string
                #print(soup1[1].string)
                next(status=STATUS_JUDGING,
                    case={
                        'status': self.SResult[soup1[2].string],
                        'score': int(soup1[1].string[7:]),
                        'time_ms': int(soup1[3].string[6:-2]),
                        'memory_kb': int(soup1[4].string[8:-2]),
                        'judge_text': soup1[2].string+"["+soup1[1].string[7:]+"]"},
                    progress=99)
                finalStatus = max(finalStatus,self.SResult[soup1[2].string])
        if watext != "":
            watext = watext + "\n---------------------------------\n"
            watext = watext + "This submission is posted to " + self.BASE_OJ + "(UOJ) by " + self.username[self.now]
        else:
            watext = "This submission is posted to " + self.BASE_OJ + "(UOJ) by " + self.username[self.now]
        #print(1)
        end(status=finalStatus,
                 score=int(fscore),
                 time_ms=int(ftime),
                 memory_kb=int(fmemory),
                 judge_text=watext)

class DBzojJudge(UOJJudge):
    BASE_OJ = "DarkBZOJ"
    BASE_URL = "https://darkbzoj.tk"

class VJudge:
    SLanguage = {}
    SLang_VOJ = {"pas":"PASCAL","cc":"CPP","c":"C","java":"JAVA","py":"PYTHON","py3":"PYTHON","cs":"CSHARP","php":"OTHER","hs":"OTHER","rs":"OTHER","go":"OTHER","js":"OTHER","rb":"RUBY"}
    SResult = {
        "PENDING":STATUS_COMPILING,
        "SUBMITTED":STATUS_COMPILING,
        "QUEUEING":STATUS_COMPILING,
        "COMPILING":STATUS_COMPILING,
        "JUDGING":STATUS_JUDGING,
        "RUNNING":STATUS_JUDGING,
        
        "SUBMIT_FAILED_TEMP":STATUS_SYSTEM_ERROR,
        "SUBMIT_FAILED_PERM":STATUS_SYSTEM_ERROR,
        "AC":STATUS_ACCEPTED,
        "PE":STATUS_WRONG_ANSWER,
        "WA":STATUS_WRONG_ANSWER,
        "OLE":STATUS_WRONG_ANSWER,
        "RE":STATUS_RUNTIME_ERROR,
        "TLE":STATUS_TIME_LIMIT_EXCEEDED,
        "MLE":STATUS_MEMORY_LIMIT_EXCEEDED,
        "CE":STATUS_COMPILE_ERROR,
        "FAILED_OTHER":STATUS_WRONG_ANSWER,
    }
    BASE_OJ = "POJ"
    DB_db = None
    DB_cursor = None
    
    def __init__(self):
        self.DB_db = pymysql.connect("localhost","admin","ly520520","vhoj" )
        self.DB_cursor = self.DB_db.cursor()
    
    def Submit(self,pid,code,lang):
        sql = """INSERT INTO `t_submission` (`C_STATUS`,`C_TIME`,`C_MEMORY`, `C_SUBTIME`, `C_PROBLEM_ID`, `C_USER_ID`, `C_CONTEST_ID`, `C_LANGUAGE`, `C_SOURCE`, `C_ISOPEN`, `C_DISP_LANGUAGE`, `C_USERNAME`, `C_ORIGIN_OJ`, `C_ORIGIN_PROB`, `C_IS_PRIVATE`, `C_ADDITIONAL_INFO`, `C_REAL_RUNID`, `C_REMOTE_ACCOUNT_ID`, `C_QUERY_COUNT`, `C_STATUS_UPDATE_TIME`, `C_REMOTE_SUBMIT_TIME`, `C_STATUS_CANONICAL`, `C_SOURCE_LENGTH`, `C_LANGUAGE_CANONICAL`, `C_CONTEST_NUM`) VALUES ('Pending', '0', '0', '%s', '5', '2', NULL, '%s', '%s', '0', '%s', 'BMJudge', '%s', '%s', '0', NULL, NULL, NULL, '0', NULL, NULL, 'PENDING', NULL, '%s', NULL)""" % \
              (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),self.SLanguage[lang],pymysql.escape_string(code),lang,self.BASE_OJ,pid,self.SLang_VOJ[lang])
        try:
           # 执行sql语句
           self.DB_cursor.execute(sql)
           last_id = self.DB_cursor.lastrowid
           # 执行sql语句
           self.DB_db.commit()
           return str(last_id)
        except:
           # 发生错误时回滚
           self.DB_db.rollback()
           return "-1"
    
    def Monitor(self,rid,next,end):
        sql = "SELECT `C_ID`, `C_TIME`, `C_MEMORY`, `C_STATUS_CANONICAL`, `C_STATUS` FROM `t_submission` WHERE `C_ID` = "+rid
        stat = STATUS_COMPILING
        stat_text = ""
        stat_text_old = ""
        time_ms = 0
        memory_kb = 0
        count = 0
        data2 = {
            'draw':'1',
            'columns[0][data]':'0',
            'columns[0][name]':'',
            'columns[0][searchable]':'true',
            'columns[0][orderable]':'false',
            'columns[0][search][value]':'',
            'columns[0][search][regex]':'false',
            'columns[1][data]':'1',
            'columns[1][name]':'',
            'columns[1][searchable]':'true',
            'columns[1][orderable]':'false',
            'columns[1][search][value]':'',
            'columns[1][search][regex]':'false',
            'columns[2][data]':'2',
            'columns[2][name]':'',
            'columns[2][searchable]':'true',
            'columns[2][orderable]':'false',
            'columns[2][search][value]':'',
            'columns[2][search][regex]':'false',
            'columns[3][data]':'3',
            'columns[3][name]':'',
            'columns[3][searchable]':'true',
            'columns[3][orderable]':'false',
            'columns[3][search][value]':'',
            'columns[3][search][regex]':'false',
            'columns[4][data]':'4',
            'columns[4][name]':'',
            'columns[4][searchable]':'true',
            'columns[4][orderable]':'false',
            'columns[4][search][value]':'',
            'columns[4][search][regex]':'false',
            'columns[5][data]':'5',
            'columns[5][name]':'',
            'columns[5][searchable]':'true',
            'columns[5][orderable]':'false',
            'columns[5][search][value]':'',
            'columns[5][search][regex]':'false',
            'columns[6][data]':'6',
            'columns[6][name]':'',
            'columns[6][searchable]':'true',
            'columns[6][orderable]':'false',
            'columns[6][search][value]':'',
            'columns[6][search][regex]':'false',
            'columns[7][data]':'7',
            'columns[7][name]':'',
            'columns[7][searchable]':'true',
            'columns[7][orderable]':'false',
            'columns[7][search][value]':'',
            'columns[7][search][regex]':'false',
            'columns[8][data]':'8',
            'columns[8][name]':'',
            'columns[8][searchable]':'true',
            'columns[8][orderable]':'false',
            'columns[8][search][value]':'',
            'columns[8][search][regex]':'false',
            'columns[9][data]':'9',
            'columns[9][name]':'',
            'columns[9][searchable]':'true',
            'columns[9][orderable]':'false',
            'columns[9][search][value]':'',
            'columns[9][search][regex]':'false',
            'columns[10][data]':'10',
            'columns[10][name]':'',
            'columns[10][searchable]':'true',
            'columns[10][orderable]':'false',
            'columns[10][search][value]':'',
            'columns[10][search][regex]':'false',
            'columns[11][data]':'11',
            'columns[11][name]':'',
            'columns[11][searchable]':'true',
            'columns[11][orderable]':'false',
            'columns[11][search][value]':'',
            'columns[11][search][regex]':'false',
            'order[0][column]':'0',
            'order[0][dir]':'desc',
            'start':'0',
            'length':'20',
            'search[value]':'',
            'search[regex]':'false',
            'un':'',
            'OJId':'All',
            'probNum':'',
            'res':'0',
            'language':'',
            'orderBy':'run_id'
        }
        data1 = """callCount=1
page=/vjudge/problem/status.action
httpSessionId=
scriptSessionId=BFADD655A107EB49B4228F916E0C4AF3943
c0-scriptName=judgeService
c0-methodName=getResult
c0-id=0
c0-e1=string:%s
c0-param0=Array:[reference:c0-e1]
batchId=1
""" % rid
        res = requests.get("http://127.0.0.1:8080/vjudge/problem/status.action")
        res = requests.post("http://127.0.0.1:8080/vjudge/problem/fetchStatus.action",data=data2)
        res = requests.post("http://127.0.0.1:8080/vjudge/dwr/call/plaincall/judgeService.getResult.dwr",data=data1)
        try:
            # 执行SQL语句
            self.DB_cursor.execute(sql)
            # 获取所有记录列表
            results = self.DB_cursor.fetchall()
            for row in results:
                stat = self.SResult[row[3]]
                stat_text = row[4]
                time_ms = row[1]
                memory_kb = row[2]
                print(rid,stat_text)
            self.DB_db.commit()
        except:
            raise
        
        while stat==STATUS_COMPILING or stat==STATUS_JUDGING:
            if stat_text != stat_text_old:
                next(status=stat,
                    case={
                        'status': stat,
                        'score': 0,
                        'time_ms': time_ms,
                        'memory_kb': memory_kb,
                        'judge_text': stat_text},
                    progress=0)
                stat_text_old = stat_text
            else:
                next(status=stat, progress=0)
            time.sleep(1)
            
            if count%10==0:
                res = requests.get("http://127.0.0.1:8080/vjudge/problem/status.action")
                res = requests.post("http://127.0.0.1:8080/vjudge/problem/fetchStatus.action",data=data2)
                res = requests.post("http://127.0.0.1:8080/vjudge/dwr/call/plaincall/judgeService.getResult.dwr",data=data1)
            try:
                # 执行SQL语句
                self.DB_cursor.execute(sql)
                # 获取所有记录列表
                results = self.DB_cursor.fetchall()
                for row in results:
                    stat = self.SResult[row[3]]
                    stat_text = row[4]
                    time_ms = row[1]
                    memory_kb = row[2]
                self.DB_db.commit()
                print(stat_text)
            except:
                raise
            
            count += 1
        
        sql = "SELECT `C_ID`, `C_TIME`, `C_MEMORY`, `C_STATUS_CANONICAL`, `C_STATUS`, `C_ADDITIONAL_INFO`, `C_REAL_RUNID`, `C_REMOTE_ACCOUNT_ID` FROM `t_submission` WHERE `C_ID` = "+rid
        try:
            # 执行SQL语句
            self.DB_cursor.execute(sql)
            # 获取所有记录列表
            results = self.DB_cursor.fetchall()
            for row in results:
                stat = self.SResult[row[3]]
                stat_text = row[4]
                time_ms = row[1]
                memory_kb = row[2]
                runid = row[6]
                raccount = row[7]
                compiler_text = row[5]
                judge_text = "Judged by BMVJudge, BMVJudge Id : %s.\nRemote Account : %s , Remote OJ Id : %s" % \
                                (str(row[0]),raccount,runid)
        except:
            raise
        
        if compiler_text:
            next(compiler_text=compiler_text)
        
        if stat == STATUS_COMPILE_ERROR:
            next(status=stat,
                case={
                    'status': stat,
                    'score': 0,
                    'time_ms': time_ms,
                    'memory_kb': memory_kb,
                    'judge_text': stat_text},
                progress=0)
            end(status=STATUS_COMPILE_ERROR,
                 score=0,
                 time_ms=0,
                 memory_kb=0,
                 judge_text=judge_text)
        else:
            if stat == STATUS_ACCEPTED:
                score = 100
            else:
                score = 0
            next(status=STATUS_JUDGING,
                case={
                    'status': stat,
                    'score': score,
                    'time_ms': time_ms,
                    'memory_kb': memory_kb,
                    'judge_text': stat_text},
                progress=100)
            end(status=stat,
                     score=score,
                     time_ms=time_ms,
                     memory_kb=time_ms,
                     judge_text=judge_text)

class CFJudge(VJudge):
    SLanguage = {"pas":4,"cc":42,"c":43,"java":36,"py":7,"py3":31,"cs":9,"php":6,"hs":12,"rs":49,"go":32,"js":34,"rb":8}
    BASE_OJ = "CodeForces"
    
class POJJudge(VJudge):
    SLanguage = {"pas":3,"cc":0,"c":1,"java":2,"py":5,"py3":4,"cs":6}
    BASE_OJ = "POJ"
    
class HDUJudge(VJudge):
    SLanguage = {"pas":4,"cc":0,"c":1,"java":5,"py":3,"py3":2,"cs":6}
    BASE_OJ = "HDU"
    
'''        
def nxt(compiler_text="",status="",case="",progress=""):
    print("---------next----------")
    print(compiler_text)
    print(status)
    print(case)
    print(progress)

def end(status,score,time_ms,memory_kb):
    print("---------next----------")
    print(status)
    print(score)
    print(time_ms,memory_kb)

bzoj = BZOJJudge('zhonghuatu','ly520520')
while True:
    if bzoj.CheckSession():
        print("YES")
        code = """#include<bits/stdc++.h>
using namespace std;
int main(){
    int a,b;
    cin>>a>>b;
    cout<<a+b<<endl;
    return 0;
}"""
        rid = bzoj.Submit("1000",code,"cc")
        #rid = input("请输入ID：")
        bzoj.Monitor("1000",rid,nxt,end)
        time.sleep(10)
    else:
        print("NO")
        bzoj.Login()
    time.sleep(1)'''
