"""Summary

Attributes:
    datasets (TYPE): Description
"""
import requests
from xml.etree.ElementTree import fromstring
from pprint import pprint
import re
import json
import jsbeautifier
import datetime
import pandas
import argparse
import tabulate
import dateparser
import warnings
import plotext as plt
import numpy as np
from matplotlib import pyplot as plt2
from bs4 import BeautifulSoup as bs

# Ignore dateparser warnings regarding pytz
warnings.filterwarnings(
    "ignore",
    message="The localize method is no longer necessary, as this time zone supports the fold attribute",
)

DATE_FORMATS = ["%d.%m.%Y","%Y-%m-%d","%m/%d/%Y","%Y"]
STATION_TYPES = {4:"Automatic station",
				 3:"Main station",
				 2:"Climatological station",
				 1:"Rainfall station"}

def jsonify(j):
	"""Converts JS code of object into JSON valid code, stringifying variables
	
	Args:
	    j (TYPE): Description
	
	Returns:
	    TYPE: Description
	"""
	out = ""
	inside_string = False
	new_string = False
	string_type = None
	for i in range(len(j)):
		if j[i] in ["'",'"']:
			if inside_string:
				if string_type == j[i]:
					inside_string = False
					new_string = False
				else:
					pass
			else:
				inside_string = True
				string_type = j[i]

		elif j[i] in ["{","}","[","]","(",")"]:
			if inside_string:
				if new_string:
					inside_string = False
					new_string = False
					out+='"'
			pass
		elif j[i] == " ":
			pass
		elif j[i] in [":",","]:
			if new_string:
				inside_string = False
				new_string = False
				out+='"'
		else:
			if not inside_string:
				inside_string = True
				new_string = True
				out+='"'
				string_type = '"'
		out+=j[i]
	return out

def get_datasets():
	"""Summary
	
	Returns:
	    TYPE: Description
	"""
	out = []
	r = requests.get("https://meteo.arso.gov.si/webmet/archive/settings.xml?lang=en")
	
	if r.status_code == 200:

		root = fromstring(r.content.decode("utf-8"))
		text = root.text
		j = re.search(r"^AcademaPUJS.set\((.+)\)$",text)[1]

		a = json.loads(jsonify(j))

		for api_type in a["dt"]:
			dv = api_type["dv"][0]
			for group in dv["groups"]:
				for param, param_value in group["params"].items():
					out.append({
						"id":param_value["pid"],
						"short_string":param_value["s"],
						"long_string":param_value["l"],
						"group":group["gid"],
						"group_description":group["desc"],
						"api_type":dv["url"],
						"api_desciption":api_type["desc"],
						"has_interval":api_type["interval"],
						"type_datepicker":api_type["datepicker"],
						"min_date":api_type["mindate"],
						"type":param_value["t"],
					})

		return pandas.DataFrame.from_dict(out)
	else:
		print(r.text)
		exit()

def get_locations(d1,d2,types):
	"""Get available locations per types and selected dates
	
	Args:
	    d1 (str): YYYY-MM-DD
	    d2 (str): YYYY-MM-DD
	    types (list): ["1","2","3","4"] or any combination
	"""
	out = []
	types_str = ",".join(types)
	url = "https://meteo.arso.gov.si/webmet/archive/locations.xml?d1=%s&d2=%s&type=%s"%(d1,d2,types_str)
	print(url)
	r = requests.get(url)
	root = fromstring(r.content.decode("utf-8"))
	text = root.text
	j = re.search(r"^AcademaPUJS.set\((.+)\)$",text)[1]
	a = json.loads(jsonify(j))
	for k,v in a["points"].items():
		out.append({
			"id":k.replace("_",""),
			"location_name":v["name"],
			"lon":v["lon"],
			"lat":v["lat"],
			"alt":v["alt"],
			"type":v["type"],
			"type_desc":STATION_TYPES[int(v["type"])],
		})
	out = sorted(out, key=lambda x: x["location_name"])
	return pandas.DataFrame.from_dict(out)

datasets = get_datasets()
#get_locations(datetime.datetime(year=2020,month=9,day=10),datetime.datetime(year=2020,month=9,day=11),["1","2","3"])

def get_data(api_type,group,params,loc,d1,d2):
	out = []
	url = "https://meteo.arso.gov.si/webmet/archive/data.xml?lang=en&vars=%s&group=%s&type=%s&id=%s&d1=%s&d2=%s" % (
		params,group,api_type,loc,d1,d2
	)
	r = requests.get(url)
	print(url)

	if r.status_code == 200:
		table = []

		root = fromstring(r.content.decode("utf-8"))
		text = root.text
		j = re.search(r"^AcademaPUJS.set\((.+)\)$",text)[1]
		as_json = jsonify(j)
		a = json.loads(as_json)
		for loc_id,points in a["points"].items():
			for timestamp,values in points.items():
				time = datetime.datetime(year=1800,month=1,day=1)+datetime.timedelta(minutes=int(timestamp.replace("_","")))
				time_str = time.strftime("%Y-%m-%d %H:%M")
				out.append({
					"location_id":loc_id,
					"timestamp":timestamp,
					"time":time,
					"time_str":time_str,
					"values":values,
					"parameters":a["params"],
				})

				table.append([time_str])

				for p_id,_ in a["params"].items():
					if p_id in values.keys():
						p_val = values[p_id]
					else:
						p_val = ""
					
					if p_val == "yes":
						val = 1
					elif p_val == "no":
						val = 0
					elif p_val != "":
						val = float(p_val)
					else:
						val = None
						
					out[-1]["data_"+p_id] = val
					if p_val != "":
						table[-1].append(p_val+" "+a["params"][p_id]["unit"])
					else:
						table[-1].append("")
		print(tabulate.tabulate(table,headers=["Date",*[v["s"] for k,v in a["params"].items()]]))
		return pandas.DataFrame.from_dict(out)
	else:
		print(r.text)
		exit()

def plot_data(data,title):
	COLORS = ["blue+", "green+", "red+", "cyan+", "magenta+", "yellow", "gray",
				  "blue", "green", "red", "cyan", "magenta", "gold", "black"]

	datetimes = list(data.time)
	dates_ticks = [d.strftime("%y-%m-%d %H:%M") for d in datetimes]
	plt.clear_figure()
	rows,columns = data.shape
	j=0
	for p_id in data.loc[0,"parameters"].keys():
		y = list(data.loc[:,"data_"+str(p_id)])
		if not y.count(None) == len(y):
			plt.plot(y,color=COLORS[j],label=data.loc[0,"parameters"][p_id]["s"])
			j+=1
	plt.xticks(range(len(dates_ticks)),dates_ticks)
	plt.canvas_color("black")
	plt.axes_color("black")
	plt.ticks_color("white")
	plt.show()


def main():

	debug = False

	print("Select API:")
	apis = datasets.api_type.unique()
	[print(i, apis[i]) for i in range(len(apis))]
	if debug:
		num_api = 0
	else:
		num_api = int(input(">"))
	selected = datasets.loc[datasets["api_type"]==apis[num_api]].reset_index(drop=True)
	
	print("Select group:")
	groups = selected.group.unique()
	[print(i, apis[i]) for i in range(len(groups))]
	if debug:
		num_group = 0
	else:
		num_group = int(input(">"))
	selected = selected.loc[selected["group"]==groups[num_group]].reset_index(drop=True)
	
	print("Select parameters:")
	for i in range(len(selected.index)):
		print(i,selected.loc[i].short_string)

	if debug:
		params = "3,4,5"
	else:
		params = input(">")
	params_selected_list = params.split(",")
	params_ints = [int(param) for param in params_selected_list]
	p = selected.loc[params_ints[0]]
	params_ids = ",".join([selected.loc[params_ints[i]].id for i in range(len(params_selected_list))])
	param_names = ",".join([selected.loc[params_ints[i]].long_string for i in range(len(params_selected_list))])
	
	if debug:
		d1 = "2015-01-01"
	else:
		d1 = dateparser.parse(input("Start date:\n"),date_formats=DATE_FORMATS).strftime("%Y-%m-%d")
	if debug:
		d2 = "2015-01-02"
	else:
		d2 = dateparser.parse(input("End date:\n"),date_formats=DATE_FORMATS).strftime("%Y-%m-%d")

	locs = get_locations(d1,d2,p.type)
	for i in range(len(locs.index)):
		_l = locs.loc[i]
		print(i,_l.location_name,"("+_l.type_desc+")")
	if debug:
		num_loc = 1
	else:
		num_loc = int(input(">"))
	l = locs.loc[num_loc]

	data = get_data(api_type=p.api_type,
			 group=p.group,
			 params=params_ids,
			 loc=l.id,
			 d1=d1,
			 d2=d2)

	plot_data(data,param_names)


main()