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
	session = []
	username = []
	password = []
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
			self.session[i].cookies = cookielib.LWPCookieJar(filename = "YBTcookies"+str(i)+".txt")
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
		print("YBT Account changes into "+self.username[self.now])
	
	def CheckSession(self):
		url = "http://ybt.ssoier.cn:8088"
		res = self.session[self.now].get(url, headers=HEADERS)
		res.encoding = 'utf-8'
		soup = BeautifulSoup(res.text,"lxml").find("th",width="30%").contents[1]
		return soup.name=='table'
	
	def Login(self):
		print(self.session[self.now].cookies)
		url = "http://ybt.ssoier.cn:8088/login.php"
		data={'username':self.username[self.now],'password':self.password[self.now],'login':'登录'}
		res = self.session[self.now].post(url,data=data,headers=HEADERS)
		res.encoding = 'utf-8'
		self.session[self.now].cookies.save()
		
	def Submit(self,pid,code,lang):
		data = {
			"user_id" : self.username[self.now],
			"problem_id" : pid,
			"language" : self.SLanguage[lang],
			"source" : code,
			"submit" : "提交"
		}
		url = "http://ybt.ssoier.cn:8088/action.php"
		res = self.session[self.now].post(url,data=data,headers=HEADERS)
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
		res = self.session[self.now].get(url,headers=HEADERS)
		res.encoding = 'utf-8'
		staText = res.text.split(":")
		while staText[4] == "Waiting" or staText[4] == "Judging":
			if staText[4] == "Waiting":
				next(status=STATUS_COMPILING, progress=0)
			else:
				next(status=STATUS_JUDGING, progress=0)
			time.sleep(1)
			res = self.session[self.now].get(url,headers=HEADERS)
			res.encoding = 'utf-8'
			staText = res.text.split(":")
		if staText[4] == "Compile Error":
			url = "http://ybt.ssoier.cn:8088/show_ce_info.php?runid="+rid
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
		if staText[4][0]=="Accepted":
			total_score = 100
			total_status = STATUS_ACCEPTED
		else:
			total_score = int(staText[4][1])
			total_status = STATUS_WRONG_ANSWER
		for i in range(0,len(staText[5])):
			if staText[5][i]=="": continue
			if staText[5][i][0]=="AC":
				score = 100//(len(staText[5])-1)
			else:
				score = 0
			staText[5][i] = staText[5][i].split("|")
			staText[5][i][1] = staText[5][i][1].split("_")
			total_memory_usage_kb += int(staText[5][i][1][0])
			total_time_usage_ms += int(staText[5][i][1][1])
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
		"Output_Limit_Exceeded":STATUS_WRONG_ANSWER,
		"Runtime_Error":STATUS_RUNTIME_ERROR,
		"Time_Limit_Exceeded":STATUS_TIME_LIMIT_EXCEEDED,
		"Memory_Limit_Exceeded":STATUS_MEMORY_LIMIT_EXCEEDED,
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
				return "-2"
	
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
			soup = str(BeautifulSoup(res.text,"lxml")).find("pre").string
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