# -*- coding: utf-8 -*-
import pandas as pd
import random
import time

class IdentityCardGenerater(object):
	def __init__(self):
		self.addr = pd.read_csv('addrId.csv', dtype={'addrId': str, 'addr': str})
		
	def fake(self):
		rand = random.randint(0, len(self.addr)-1)
		adId = self.addr.loc[rand,'addrId']
		adNam = self.addr.loc[rand,'addr']

		year = str(random.randint(1948, int(time.strftime('%Y')) - 18))
		month = random.randint(1, 12)
		month = str(month) if month >= 10 else '0' + str(month)
		day = random.randint(1, 28)
		day = str(day) if day >= 10 else '0' + str(day)

		order = str(random.randint(100, 999))

		idCard = str(adId) + year + month + day + order + '0'
		check = (12-(sum([int(idCard[i])*((2**i)%11) for i in range(18)])%11))%11
		check = str(check) if check < 10 else 'X'

		idCard = idCard[:-1] + check
	
		return idCard

	def checkIdCard(self, idCard):
		idCard = str(idCard)
		res = self.addr[self.addr.addrId == idCard[:6]]
		if len(res) > 0:
			index = res.index[0]
			adNam = res.loc[index, 'addr']
			print 'Address %s' % (adNam)
			try:
				age = int(time.strftime("%Y", time.localtime(time.time() - 
							time.mktime(time.strptime(idCard[6:14],"%Y%m%d"))))) - 1970
				print 'Age %d' % (age)
				check = idCard[-1]
				idCard = idCard[:-1] + '0'
				new_check = (12-(sum([int(idCard[17-i])*((2**i)%11) for i in range(18)])%11))%11
				new_check = str(new_check) if new_check < 10 else 'X'
				if check == new_check:
					return True
				else:
					print 'IdentityCard number invalid %s' %(idCard[:-1]+check) 
			except:
				print 'IdentityCard date time invalid %s' %(idCard[6:14]) 

		return False
