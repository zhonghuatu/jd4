import requests
from bs4 import BeautifulSoup
from bson import objectid
import pymongo
import time
import tomd
import datetime
import json
import re
import http.cookiejar as cookielib

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
	session = None
	username = ""
	password = ""
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
	
	def __init__(self, username, password):
		self.username = username
		self.password = password
		self.session = requests.Session()
		self.session.cookies = cookielib.LWPCookieJar(filename = "YBTcookies.txt")
		try:
			self.session.cookies.load()
			for item in self.session.cookies:
				print(item)
		except:
			print("Cookie 未能加载")
		print("Init")
	
	def CheckSession(self):
		url = "http://ybt.ssoier.cn:8088"
		res = self.session.get(url, headers=HEADERS)
		res.encoding = 'utf-8'
		soup = BeautifulSoup(res.text,"lxml").find("th",width="30%").contents[1]
		return soup.name=='table'
	
	def Login(self):
		print(self.session.cookies)
		url = "http://ybt.ssoier.cn:8088/login.php"
		data={'username':self.username,'password':self.password,'login':'登录'}
		res = self.session.post(url,data=data,headers=HEADERS)
		res.encoding = 'utf-8'
		self.session.cookies.save()
		
	def Submit(self,pid,code,lang):
		data = {
			"user_id" : self.username,
			"problem_id" : pid,
			"language" : self.SLanguage[lang],
			"source" : code,
			"submit" : "提交"
		}
		url = "http://ybt.ssoier.cn:8088/action.php"
		res = self.session.post(url,data=data,headers=HEADERS)
		res.encoding = 'utf-8'
		if res.text.find("提交频繁啦！")!=-1:
			return "-1"
		else :
			try:
				return BeautifulSoup("<a>"+res.text+"</a>","lxml").script.string.replace("'","").split("=")[-1].replace(";","")
			except:
				return "-2"
	
	def Monitor(self,rid,next,end):
		url = "http://ybt.ssoier.cn:8088/statusx1.php?runidx="+rid
		res = self.session.get(url,headers=HEADERS)
		res.encoding = 'utf-8'
		staText = res.text.split(":")
		while staText[4] == "Waiting" or staText[4] == "Judging":
			if staText[4] == "Waiting":
				next(status=STATUS_COMPILING, progress=0)
			else:
				next(status=STATUS_JUDGING, progress=0)
			time.sleep(1)
			res = self.session.get(url,headers=HEADERS)
			res.encoding = 'utf-8'
			staText = res.text.split(":")
		if staText[4] == "Compile Error":
			url = "http://ybt.ssoier.cn:8088//show_ce_info.php?runid="+rid
			res = self.session.get(url,headers=HEADERS)
			res.encoding = 'utf-8'
			soup = str(BeautifulSoup(res.text,"lxml").find("td",attrs={"class":"ceinfo"})).replace('<td class="ceinfo">','').replace('</td>','').replace('\n','').replace('<br/>','\n').replace('\n\n','\n')
			next(compiler_text=message)
			end(status=STATUS_COMPILE_ERROR,
                 score=0,
                 time_ms=0,
                 memory_kb=0)
			return
		staText[4] = staText[4].split("|")
		staText[5] = staText[5].split(",")
		total_time_usage_ms = 0
		total_memory_usage_kb = 0
		if staText[4][0]=="Accept":
			total_score = 100
			total_status = STATUS_ACCEPTED
		else:
			total_score = int(staText[4][1])
			total_status = STATUS_WRONG_ANSWER
		for i in range(0,len(staText[5])):
			if staText[5][i][0]=="AC":
				score = total_score//(len(staText[5])-1)
			else:
				score = 0
			if staText[5][i]=="": continue
			staText[5][i] = staText[5][i].split("|")
			staText[5][i][1] = staText[5][i][1].split("_")
			total_memory_usage_kb += int(staText[5][i][1][0])
			total_time_usage_ms += int(staText[5][i][1][0])
			next(status=STATUS_JUDGING,
                      case={
					        'status': self.SResult[staText[5][i][0]],
                            'score': score,
                            'time_ms': int(staText[5][i][1][1]),
                            'memory_kb': int(staText[5][i][1][0]),
                            'judge_text': self.SResultTip[staText[5][i][0]]},
                      progress=99)
		end(status=total_status,
                 score=total_score,
                 time_ms=total_time_usage_ms,
                 memory_kb=total_memory_usage_kb)
			
'''
ybt = YBTJudge('BackMountOJ','houshan123')
while True:
	if ybt.CheckSession():
		print("YES")
		code = """#include<bits/stdc++.h>
using namespace std;
int main(){
    int a,b;
    cin>>a>>b;
    cout<<a+b<<endl;
    return 0;
}"""
		#print(ybt.submit("1000",code,1))
		rid = input("请输入ID：")
		ybt.monitor(rid,0,0)
		time.sleep(10)
	else:
		print("NO")
		ybt.Login()
	time.sleep(3)'''