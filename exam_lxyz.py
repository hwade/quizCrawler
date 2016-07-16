#! /usr/env/bin python
# coding:utf-8
# author: hwade
# email: hwade_good@163.com

from bs4 import BeautifulSoup
from random import random,randint
from PIL import Image
# import pytesseract
import cookielib
import urllib
import urllib2
import re
import sys
import time

BASE_URL = 'http://ks.gdycjy.gov.cn' # 基础域名

# 预先使用几个设定好的用户来撞本次试题库，可以加快程序运行速度
# 也可以设置成自动生成伪用户，创建试题库的过程会较为繁琐（当预设的伪用户失效时可用）
IS_AUTO_FAKE_USER = True
# 为了避免漏掉题目，设置10个伪用户，可能导致较长的运行时间
FAKE_USER_NUM = 10
# 预设的伪用户
FAKE_USERS = []

STANDARD_ANSWERS = {}				# 试题的标准答案
AREA_NAME = '省委教育工委发文高校'	# 默认为高校学生，其他类型的请自己手动修改啦 ~.~

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
	except:
		print '预设伪用户失效，请将IS_AUTO_FAKE_USER设为True'
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

def genFakeUser():
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
			'areaName': AREA_NAME
		}
		uuid = getuuid(patchca, postData)
		if uuid == '':
			print 'fake user 获取 uuid 失败。'
			return 

		# 保存伪用户uuid，下次再运行可直接使用
		FAKE_USERS.append(uuid)

		# 获得题目编号
		ques = getQuestions(uuid)
		
		# 时间太小会导致服务器报错
		time.sleep(15)

		# 提交答案，随缘作答
		submitAnswers(uuid,ques)
		# 更新标准答案
		updateStandardAns(uuid)
	else:
		# 识别验证码成功
		print '暂时木有'

def checkUserIsRegist(mobile):
	### 检测用户是否已经注册
	postD = urllib.urlencode({'mobile':mobile})
	res = urllib2.urlopen(BASE_URL + '/dzTest.shtml?act=checkUserSubmit', data=postD)
	data = res.read()
	# print data
	if data.find('true') > -1:
		# 该用户已注册
		return False
	return True

def getQuestions(uuid):
	### 获取题目
	ques = []
	for i in range(1,6):
		# 1~5页问题
		html = getHtml(BASE_URL + "/kQuestion.shtml?act=getQuestions&uuid=" + uuid + "&pageNo=" + str(i))
		
		reg = r'question_[0-9]+'
		quesReg = re.compile(reg)
		queslist = re.findall(quesReg,html)
		for q in queslist:
			q = q.split("_")[1]
			ques.append(q)
	
	return list(set(ques))
	
def submitAnswers(uuid, questions):
	### 提交答案
	finalUrl = BASE_URL + "/kQuestion.shtml?act=submitOwnerAnswer&uuid=" + uuid + "&ownerAnswer="
	for q in questions:
		if STANDARD_ANSWERS.has_key(q):
			finalUrl += q + "%3A" + str(STANDARD_ANSWERS[q]) + "%2C"
			# print "(%s:%d)"%(q,STANDARD_ANSWERS[q]), 
		else:
			finalUrl += q + "%3A" + str(int(q)*3) + "%2C"
	finalUrl = finalUrl[:-3]
	# 提交答案请求，直接通过url传送答案
	html = getHtml(finalUrl)
	# print html

def updateStandardAns(uuid):
	### 更新标准答案
	global STANDARD_ANSWERS
	# 获取infoId，用来获取答案页面
	html = getHtml(BASE_URL + "/kUserPlayer.shtml?act=getKUserAnserInfoList&uuid=" + uuid)
	soup = BeautifulSoup(html)
	table = soup.find_all('table',attrs={"class":"gridtable"})[0]
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
			inputs = BeautifulSoup(str(div)).find_all("input",attrs={"type":"radio"})
			inp = ''
			for i in inputs:
				if str(i).find('checked') > -1:
					inp = i
					break
			reg = r'question_[0-9]+'
			quesReg = re.compile(reg)
			q = re.findall(quesReg,str(inp))[0]
			reg = r'[A-C]'
			ansReg = re.compile(reg)
			ans = re.findall(ansReg,str(inp.parent))

			# 正确答案选项
			inp = BeautifulSoup(str(div)).find_all("input",attrs={"class":"xhx"})
			for i in inp:
				reg = r'[A-C]'
				ansReg = re.compile(reg)
				ans = re.findall(ansReg,str(i))

			# 将 正确答案 和 对应题号 存储在全局变量STANDARD_ANSWERS
			q = q.split("_")[1]	
			if ans[0] == 'A':
				STANDARD_ANSWERS[q] = int(q)*3 - 2
			elif ans[0] == 'B':
				STANDARD_ANSWERS[q] = int(q)*3 - 1
			else:
				STANDARD_ANSWERS[q] = int(q)*3	

if __name__ == "__main__":
	''' 主函数 '''
	# 设置获取服务器cookie，否则某些请求无法通过服务器验证
	cj = cookielib.LWPCookieJar()
	cookie_support = urllib2.HTTPCookieProcessor(cj) 
	opener = urllib2.build_opener(cookie_support, urllib2.HTTPHandler)
	urllib2.install_opener(opener)
	
	# 生成伪用户，用来撞试题库，获取试题正确答案，默认10个伪用户
	if IS_AUTO_FAKE_USER == True:
		print '由于没有找到能有效识别该验证码的库（exceuse me???），所以请使用肉眼识别法！'
		print '如果有推荐的简易python验证码识别工具（除了pytesseract以外）请告诉我: \nhwade_good@163.com'
		for ui in range(FAKE_USER_NUM):	
			genFakeUser()
		# 保存fakeUsers, 便于下次直接使用，当然有时间限制（半小时还是多少不确定）
		with open('fakeUsers.txt','w') as fd:
			for uuid in FAKE_USERS:
				fd.write(uuid + '\n')
	else:
		# 采用预设的伪用户，可直接获得标准答案
		global FAKE_USERS
		with open('fakeUsers.txt','r') as fd:
			for uuid in fd.readlines():
				FAKE_USERS.append(uuid)
		print '正在获取标准答案...'
		for uuid in FAKE_USER:
			updateStandardAns(uuid)
	# print STANDARD_ANSWERS

	'''
	TODO:
	# 获取学校选项
	fd = open('schools.html','r')
	select = fd.readlines()
	fd.close()
	print str(select)
	opts = BeautifulSoup(str(select)).find_all('option',attrs={'class':'newOpt'})
	dic = {}
	for opt in opts:
		print opt.text
		dic[opt.text] = opt.val
	'''

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
		'areaName': AREA_NAME
	}
	uuid = getuuid(patchca, postData)
	if uuid == '':
		print '您获取 uuid 失败，请按标准格式注册信息'
	else:
		# 获得题目编号
		ques = getQuestions(uuid)

		# 设置完成时间
		t = input('设置完成时间(单位s，必须20s以上):')
		time.sleep(t)

		# 提交标准答案
		submitAnswers(uuid,ques)
	print '完成！'
	
