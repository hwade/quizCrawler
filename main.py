#! /usr/env/bin python
# coding:utf-8
# author: hwade
# email: hwade_good@163.com

from bs4 import BeautifulSoup
from random import random,randint
from PIL import Image
# import pytesseract
import pandas as pd
import cookielib
import urllib
import urllib2
import os
import re
import sys
import time

BASE_URL = 'http://ks.gdycjy.gov.cn' # 基础域名

# 预先使用几个设定好的用户来撞本次试题库，可以加快程序运行速度
# 也可以设置成自动生成伪用户，创建试题库的过程会较为繁琐（当预设的伪用户失效时可用）
IS_AUTO_FAKE_USER = True
# 为了避免漏掉题目，设置10个伪用户，可能导致较长的运行时间
FAKE_USER_NUM = 1
# 预设的伪用户
FAKE_USERS = []
QUES_BANK_LIB = 'ques_bank.csv'		# 本地题库
STANDARD_ANSWERS = {}				# 试题的标准答案
AREA_NAME = '省委教育工委发文高校'	# 默认为高校学生，其他类型的请自己手动修改啦 ~.~
UNIT_NAME = '华南理工大学'			# 


def getAnsHistoryFromFile():
	### 从文件中读取历史题库答案
	file_obj = open("standardAnswer.txt","r")
	data = file_obj.read()
	file_obj.close()

	return eval(data)

def writeAnsToFile(standard_ans):
	### 将当前标准答案存入题库	
	file_obj = open("standardAnswer.txt","w")
	file_obj.writelines(str(standard_ans))
	file_obj.close()

def autoRegcPatchca():
	### 自动识别验证码

	return False

def showPatchca():
	### 无法自动识别验证码时，显示验证码由用户自己识别
	image = Image.open('patchca.png')
	image.show()

def getHtml(url):
	### 获取HTML对象
	try:
		page = urllib2.urlopen(url)
		html = page.read()	
		return html
	except Exception, e:
		print '预设伪用户失效，请将IS_AUTO_FAKE_USER设为True', e
		sys.exit()
		

def login(patchca):
	### 模拟登录
	chkPatchcaUrl = BASE_URL + "/kQuestion.shtml?act=patchcaValidate&patchcafield=" + patchca
	res = urllib2.urlopen(chkPatchcaUrl, data=urllib.urlencode({'suggest':patchca}))
	data = res.read()

	while data == 'invalidate':
		patchca = input('验证码失效/错误，请重新输入：')
		login(patchca)
		
def getuuid(patchca, pData):
	### 获取用户uuid
	uuidUrl = BASE_URL + '/kQuestion.shtml?act=saveKUserPlayer&patchca=' + patchca
	pData = urllib.urlencode(pData)
	res = urllib2.urlopen(uuidUrl, data=pData)
	data = res.read()
	# print data
	if data.find('true') > -1:
		return data.split('"')[3]
	return ''

def genPatchca():
	### 产生验证码
	rand = str(random())
	res = urllib2.urlopen(BASE_URL + '/patchca.png?' + rand)
	data = res.read()

	# 生成临时的验证码图片
	with open('patchca.png','wb') as fd:
		for chunk in data:
			fd.write(chunk)

def genFakeUser(quesBank):
	### 伪造用户，获取正确答案	
	global FAKE_USERS
	genPatchca()

	# 识别验证码
	if autoRegcPatchca() == False:
		# 若不能识别验证码则使用肉眼识别法
		showPatchca()
		patchca = str(input('请输入验证码(左上角图片)：'))
		login(patchca)

		# 随机生成电话号码
		fakeMobile = '150' + str(randint(10000000,99999999))
		chk_mobile = checkUserIsRegist(fakeMobile)
		while chk_mobile == False:
			fakeMobile = '150' + str(randint(10000000,99999999))
			chk_mobile = checkUserIsRegist(fakeMobile)
		postData = {
			'name': '伪名字',
			'areaId': '23',		# 高校
			'unitId': '67',		# 华工
			'patchcafield': patchca,
			'mobile': fakeMobile,
			'areaName': AREA_NAME,
			'unitName': UNIT_NAME,
			'sourceType':1
		}
		uuid = getuuid(patchca, postData)
		if uuid == '':
			print 'fake user 获取 uuid 失败。'
			return 

		# 保存伪用户uuid，下次再运行可直接使用
		FAKE_USERS.append(uuid)

		# 获得题目编号，返回本次问题id和更新的题库
		ques, quesBank = getQuestions(uuid,quesBank)	
		
		# 时间太小会导致服务器报错
		time.sleep(15)

		# 提交答案，随缘作答
		submitAnswers(uuid,ques,quesBank)

		# 更新标准答案
		mark, quesBank = updateStandardAns(uuid, quesBank)
		print 'fake user: %s %s score'%(fakeMobile, mark)
	else:
		# 识别验证码成功
		print '暂时木有'
	return quesBank

def checkUserIsRegist(mobile):
	### 检测用户是否已经注册
	postD = urllib.urlencode({'mobile':mobile, 'name': '伪名字'})
	res = urllib2.urlopen(BASE_URL + '/dzTest.shtml?act=checkUserSubmit', data=postD)
	data = res.read()
	# print data
	if data.find('true') > -1:
		# 该用户已注册
		return False
	return True

def getQuestions(uuid, quesBank):
	''' 获取题目 ''' 
	ques = []	# 存放问题id
	qaPair = []	# 问题和对应的答案，包括错误的答案
	for i in range(1,6):
		# 1~5页问题
		html = getHtml(BASE_URL + "/kQuestion.shtml?act=getQuestions&uuid=" + uuid + "&pageNo=" + str(i))
		soup = BeautifulSoup(html)
		quesDesc = soup.find_all('div',attrs={'class':'txtMg'})

		quesReg = re.compile(ur'[0-9]+[\u3001]')
		for item in quesDesc:
			qD = item.span.text
			qD = qD.split(re.findall(quesReg, qD)[0])[1]	# 问题描述

			ans = item.find_all('li')
			qID = item.input.attrs['class'][0].split('_')[1]	# 获取问题id
			ques.append(qID)
			if(len(quesBank[(quesBank.quesID==qID)&(quesBank.ansDesc==ans[0].text[3:])])>0):
				continue

			for a in ans:
				aID = a.input.attrs['value']	# 获取答案id
				aD = a.text[3:]					# 答案描述
				qaPair.append([qID, qD, aID, aD, -1])
			
	# 返回问题id和问题库
	return list(set(ques)), quesBank.append(pd.DataFrame(qaPair, columns=quesBank.columns))
	
def submitAnswers(uuid, questions, quesBank):
	''' 提交答案 '''

	finalUrl = BASE_URL + "/kQuestion.shtml?act=submitOwnerAnswer&uuid=" + uuid + "&ownerAnswer="
	for q in questions:
		try:
			if len(quesBank.loc[(quesBank['quesID']==q)&(quesBank['status']==1),'ansID'])>0:
				finalUrl += q + "%3A" \
						 + list(quesBank.loc[(quesBank['quesID']==q)&(quesBank['status']==1),'ansID'])[0] + "%2C"
			else:
				finalUrl += q + "%3A" \
						 + list(quesBank.loc[(quesBank['quesID']==q)&(quesBank['status']==-1),'ansID'])[0] + "%2C"
		except:
			print qquesBank.loc[(quesBank['quesID']==q)]
	finalUrl = finalUrl[:-3]
	# 提交答案请求，直接通过url传送答案
	html = getHtml(finalUrl)
	if not html.find('true')>-1:
		print questions
		print finalUrl
		print html

def updateStandardAns(uuid, quesBank):
	''' 更新标准答案 '''
	# 获取infoId，用来获取答案页面
	html = getHtml(BASE_URL + "/kUserPlayer.shtml?act=getKUserAnserInfoList&uuid=" + uuid)
	soup = BeautifulSoup(html)
	table = soup.find_all('table',attrs={"class":"gridtable"})[0]
	mark = table.find_all('tr')[1].find_all('td')[1].text
	href = str(BeautifulSoup(str(table)).find_all("a")[0]).split('"')[1]
	href = href.replace('&amp;','&')
	href = href.replace('answerCurHistory','getHistory')
	# print href
	for i in range(1,6):
		# 1~5页答案
		# print BASE_URL + href + uuid + "&pageNo=" + str(i)
		html = getHtml(BASE_URL + href + uuid + "&pageNo=" + str(i))
		soup = BeautifulSoup(html)
		divs = soup.find_all("div",attrs={"class":"txtMg"})
		for div in divs:
			# 默认所有checked的li为答案选项（不一定是正确答案）
			inputs = BeautifulSoup(str(div)).find_all("li")
			checked_li = ''
			for i in inputs:
				if str(i).find('checked') > -1:
					checked_li = i
					break
			qID = checked_li.input.attrs['class'][0].split('_')[1]
			ansDesc = checked_li.text[3:]
			if div.span.text.find(u'此题回答错误')>-1 :
				quesBank.loc[(quesBank.ansDesc==ansDesc)&(quesBank.quesID==qID),'status'] = 0	# 标记错误选项
			else:
				quesBank.loc[(quesBank.ansDesc==ansDesc)&(quesBank.quesID==qID),'status'] = 1	# 标记正确选项
	return mark, quesBank

if __name__ == "__main__":
	''' 主函数 '''	
	# 设置获取服务器cookie，否则某些请求无法通过服务器验证
	cj = cookielib.LWPCookieJar()
	cookie_support = urllib2.HTTPCookieProcessor(cj) 
	opener = urllib2.build_opener(cookie_support, urllib2.HTTPHandler)
	urllib2.install_opener(opener)

	# 加载本地题库
	quesBank = None
	if(os.path.exists(QUES_BANK_LIB)):
		quesBank = pd.read_csv(QUES_BANK_LIB, dtype={'ansID':str, 'quesID':str})
	else:
		quesBank = pd.DataFrame([], columns=['quesID','quesDesc','ansID','ansDesc','status'])

	# 生成伪用户，用来撞试题库，获取试题正确答案，默认10个伪用户
	for ui in range(FAKE_USER_NUM):	
		quesBank = genFakeUser(quesBank)

	# 验证码
	genPatchca()
	showPatchca()
	patchca = str(input('请输入验证码(左上角图片)：'))
	login(patchca)

	# 注册个人信息，此处用raw_input才不会报错
	name = raw_input('输入你的真实名字：')
	# school = input('选择学校对应的号码：')
	
	# 随机生成电话号码	
	mobile = input('输入你的手机号：')
	chk_mobile = checkUserIsRegist(mobile)
	while chk_mobile == False:
		mobile = input('输入你的手机号：')
		chk_mobile = checkUserIsRegist(mobile)
	postData = { 
		'name': name,
		'areaId': '23',		# 高校
		'unitId': '67',		# 华工
		'patchcafield': patchca,
		'mobile': mobile,
		'areaName': AREA_NAME,
		'unitName': UNIT_NAME,
		'sourceType':1
	}

	uuid = getuuid(patchca, postData)
	if uuid == '':
		print 'uuid error.'
	else:
		# 获得题目编号
		ques, quesBank = getQuestions(uuid,quesBank)

		# 设置完成时间
		t = input('设置完成时间(单位s，必须20s以上):')
		time.sleep(t)

		# 提交标准答案
		submitAnswers(uuid, ques, quesBank)

		mark, quesBank = updateStandardAns(uuid, quesBank)
		print '%s: %s %s score'%(name, mobile, mark)
		
	quesBank.to_csv(QUES_BANK_LIB, index=False)
	print '完成！'
