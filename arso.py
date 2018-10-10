import os
import time
import requests
import selenium
import logging
from datetime import datetime
from datetime import timedelta
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
#from selenium import Base
#from selenium.webdriver.common.action_chains import ActionChains
import csv
import openpyxl
#
logger = logging.getLogger()
dir_path = os.path.dirname(os.path.realpath(__file__))

MERILNA_POSTAJA = "NANOS"

def split_date_range(start_str,end_str,days):
	start = datetime.strptime(start_str,"%Y-%m-%d")
	end = datetime.strptime(end_str,"%Y-%m-%d")
	if start+timedelta(days=days) > end:
		return [(start_str,end_str)]
	else:
		out = []
		next_start = start
		while True:
			start_plus_delta = next_start+timedelta(days=days)
			if start_plus_delta >= end:
				out.append((datetime.strftime(next_start,"%Y-%m-%d"),datetime.strftime(end,"%Y-%m-%d")))
				break
			else:
				out.append((datetime.strftime(next_start,"%Y-%m-%d"),datetime.strftime(start_plus_delta,"%Y-%m-%d")))
				next_start = start_plus_delta+timedelta(days=1)
	return out

#d = webdriver.Chrome()
options = webdriver.ChromeOptions()
#options.add_argument("--start-maximized")
prefs = {"profile.default_content_settings.popups": 0,
         "download.default_directory": r"C:\Users\miha\Desktop\\", # IMPORTANT - ENDING SLASH V IMPORTANT
         "directory_upgrade": True}
options.add_experimental_option("prefs", prefs)
d = webdriver.Chrome(chrome_options=options)


d.get("http://meteo.arso.gov.si/met/en/app/webmet/")
while True:
	try:
		archive_button = d.find_elements_by_xpath('//td[contains(text(),"Archive")]')[0] #click archive
		print(archive_button)
		time.sleep(1)
		archive_button.click()
		time.sleep(1)
		break
	except IndexError:
		#print("passing")
		time.sleep(1)
		pass
	except selenium.common.exceptions.ElementNotVisibleException:
		time.sleep(1)
		pass

time.sleep(1)
d.find_elements_by_xpath('//p[contains(text(),"I accept")]')[0].click() #click I accept
time.sleep(1)

dates = split_date_range("2017-01-01","2017-12-31",50)
print("Dates:",dates)

wb = openpyxl.Workbook()
ws = wb.active

for repetition in range(len(dates)):
	date_from_to_send = dates[repetition][0]
	date_to_to_send = dates[repetition][1]
	period = d.find_elements_by_xpath('//td[contains(text(),"Period")]/preceding-sibling::td')[0]
	d.execute_script("arguments[0].scrollIntoView();", period)
	period.click()
	time.sleep(1)
	date_from = d.find_elements_by_xpath('//input[@class="calendar-input"]')[1] #click first date
	date_from.click()
	date_from.clear()
	date_from.send_keys(date_from_to_send) #insert date
	date_to = d.find_elements_by_xpath('//input[@class="calendar-input"]')[2]
	date_to.click()
	date_to.clear()
	date_to.send_keys(date_to_to_send) #insert date
	d.find_elements_by_xpath('//div[@class="academa-button1" and contains(text(),"Load")]')[0].click() #click load
	time.sleep(1)
	#select data
	if repetition == 0:
		d.find_elements_by_xpath('//td[contains(text(),"means and extremes - half-hourly data")]/preceding-sibling::td')[0].click() #click means and extremes
		time.sleep(2)
		d.find_elements_by_xpath('//td[contains(text(),"mean wind speed")]/preceding-sibling::td')[0].click()
		d.find_elements_by_xpath('//td[contains(text(),"mean wind direction")]/preceding-sibling::td')[0].click()
		d.find_elements_by_xpath('//td[contains(text(),"max wind gust")]/preceding-sibling::td')[0].click()
		d.find_elements_by_xpath('//td[contains(text(),"mean global energy radiation")]/preceding-sibling::td')[0].click()
		d.find_elements_by_xpath('//td[contains(text(),"mean diffusive energy radiation")]/preceding-sibling::td')[0].click()
		#d.find_elements_by_xpath('//td[contains(text(),"mean temperature")]/preceding-sibling::td')[0].click()
	time.sleep(2)
	#click stations tab 
	d.find_elements_by_xpath('//td[@class="academa-tab-out" and contains(text(),"Stations")]')[0].click()
	time.sleep(2)
	#select station
	while True:
		try:
			print("trying to click %s" % MERILNA_POSTAJA)
			lst = d.find_elements_by_xpath('//td[@class="academa-archive-form-out" and contains(text(),"%s")]' % MERILNA_POSTAJA)
			if len(lst) == 0:
				lst = d.find_elements_by_xpath('//td[@class="academa-archive-form-over" and contains(text(),"%s")]' % MERILNA_POSTAJA)
			lst[0].click()
			break
		except IndexError:
			time.sleep(1)
	a = None
	while True:
		a = d.find_elements_by_xpath('//td[@class="academa-tab-disabled" and contains(text(),"Data")]')
		if len(a) == 0:
			break
		print("Waiting for data...")
		time.sleep(1)
	save_button = d.find_elements_by_xpath('//button[@id="create" and contains(text(),"Save data")]/parent::a')[0]
	d.execute_script("arguments[0].scrollIntoView();", save_button)
	time.sleep(1)
	save_button.click()
	time.sleep(2)

	f = open(r'C:\Users\miha\Desktop\download')
	print("reader")
	reader = csv.reader(f)
	print("appending")
	#if repetition > 0:
		#reader = reader[1:]
	i = 0
	for row in reader:
	    if len(row) > 0:
	    	if not repetition == 0:
	    		if i != 0:
	    			ws.append(row)
	    	else:
	    		ws.append(row)
	    i+=1
	f.close()

	os.remove(r'C:\Users\miha\Desktop\download')

	#

	back_button = d.find_elements_by_xpath('//div[@class="academa-button1" and contains(text(),"Back")]')[0]
	back_button.click()

wb.save(r'C:\Users\miha\Desktop\file_'+MERILNA_POSTAJA.replace(" ","_")+'.xlsx')
d.quit()