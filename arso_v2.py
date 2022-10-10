"""CLI application for scraping weather data from https://meteo.arso.gov.si/webmet/archive/

Attributes:
    API_TYPES (dict): Defines data frequency in Hz
    DATE_FORMATS (list): Valid date formats
    STATION_TYPES (dict): Names of climatological station types
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
import os

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

API_TYPES = { # data frequency in Hz
	"halfhourly":1/(30*60), # halfhourly
	"daily":1/(24*60*60), # daily
	"monthly":1/(30*24*60*60), # monthly
	"yearly":1/(365*24*60*60), # yearly
	"yearly-with-months":1/(12*24*60*60), # yearly-with-months
}

def jsonify(j):
	"""Converts JS code of object into JSON valid code, stringifying variables

	Example:
	'{a:1,b:{"2":3,c:"d"}}'
	'{"a":1,"b":{"2":3,c:"d"}}'
	
	Args:
	    j (str): Javascript object code
	
	Returns:
	    str: JSON-ified code
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
	"""Calls endpoint for fetching available datasets.
	
	Returns:
	    DataFrame: Datasets from api.
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
						"api_description":api_type["desc"],
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
	"""Calls and fetches available locations as per types and selected dates.
	
	Args:
	    d1 (str): YYYY-MM-DD
	    d2 (str): YYYY-MM-DD
	    types (list): ["1","2","3","4"] or any combination
	
	Returns:
	    DataFrame: List of available locations.
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

def get_data(api_type,group,params,loc,d1,d2):
	"""Calls data-fetch API endpoint.
	
	Args:
	    api_type (str): halfhourly,daily,etc.
	    group (str): type of group
	    params (str): comma-separated list of parameters
	    loc (str): location id
	    d1 (str): start date
	    d2 (str): end date
	
	Returns:
	    DataFrame: Data
	"""
	out = []
	url = "https://meteo.arso.gov.si/webmet/archive/data.xml?lang=en&vars=%s&group=%s&type=%s&id=%s&d1=%s&d2=%s" % (
		params,group,api_type,loc,d1,d2
	)
	r = requests.get(url)
	print(url)
	if r.status_code == 200:
		root = fromstring(r.content.decode("utf-8"))
		text = root.text
		j = re.search(r"^AcademaPUJS.set\((.+)\)$",text)[1]
		as_json = jsonify(j)
		a = json.loads(as_json)
		for loc_id,points in a["points"].items():
			if api_type == "yearly-with-months":
				points_yearly = {}
				for y,_vals in points.items():
					points_yearly = {**points_yearly,**_vals["t"]}
				points = points_yearly
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

		return pandas.DataFrame.from_dict(out)
	else:
		print(r.text)
		exit()

def plot_data(data,title):
	"""Plots graph from data in terminal.
	
	Args:
	    data (DataFrame): data from get_data function
	    title (str): Title of graph
	"""
	COLORS = ["blue+", "green+", "red+", "cyan+", "magenta+", "yellow", "gray",
				  "blue", "green", "red", "cyan", "magenta", "gold", "black"]

	datetimes = list(data.time)
	dates_ticks = [d.strftime("%y-%m-%d %H:%M") for d in datetimes]
	plt.clear_figure()
	rows,columns = data.shape
	j=0
	for p_id in data.loc[0,"parameters"].keys():
		y = list(data.loc[:,"data_"+p_id])
		if not y.count(None) == len(y):
			plt.plot(y,color=COLORS[j],label=data.loc[0,"parameters"][p_id]["s"])
			j+=1
	plt.xticks(range(len(dates_ticks)),dates_ticks)
	plt.canvas_color("black")
	plt.axes_color("black")
	plt.ticks_color("white")
	plt.show()

def split_date_range(start_str,end_str,days=90,split_at_year=False):
	"""Splits date range into multiple ranges.

	Splits by days, optionally can split every new year.
	
	Args:
	    start_str (str): start date (YYYY-MM-DD)
	    end_str (str): end date (YYYY-MM-DD)
	    days (int, optional): days after which a split is done
	    split_at_year (bool, optional): splits every new year if True
	
	Returns:
	    list: list of date ranges in format [(d1_start,d1_end),(d2_start,d2_end),...]
	"""
	start = datetime.datetime.strptime(start_str,"%Y-%m-%d")
	end = datetime.datetime.strptime(end_str,"%Y-%m-%d")

	out = []
	current_range_start = start
	while True:
		current_range_end = current_range_start+datetime.timedelta(days=days)
		if split_at_year:
			if current_range_end.year > current_range_start.year:
				current_range_end = datetime.datetime(year=current_range_start.year,month=12,day=31)
		if current_range_end >= end:
			out.append((datetime.datetime.strftime(current_range_start,"%Y-%m-%d"),datetime.datetime.strftime(end,"%Y-%m-%d")))
			break
		else:
			out.append((datetime.datetime.strftime(current_range_start,"%Y-%m-%d"),datetime.datetime.strftime(current_range_end,"%Y-%m-%d")))
			current_range_start = current_range_end+datetime.timedelta(days=1)
	return out

def get_data_nice(api_type,group,params,loc,d1,d2):
	"""Helper function for getting data, implements date splitting.

	Arguments are same as for get_data function.
	
	Args:
	    api_type (str): halfhourly,daily,etc.
	    group (str): type of group
	    params (str): comma-separated list of parameters
	    loc (str): location id
	    d1 (str): start date
	    d2 (str): end date
	
	Returns:
	    DataFrame: data
	"""
	d_start = dateparser.parse(d1,date_formats=DATE_FORMATS)
	d_end = dateparser.parse(d2,date_formats=DATE_FORMATS)
	delta_t = d_end-d_start
	seconds = delta_t.total_seconds()
	days = delta_t.days
	frequency = API_TYPES[api_type]
	num_parameters = len(",".split(params))
	expected_data_points = frequency*seconds*num_parameters
	chunks_needed = expected_data_points/1000
	chunks_needed = 1 if chunks_needed < 1 else int(chunks_needed)
	days_per_chunk = int(days/chunks_needed)

	if api_type == "yearly-with-months":
		split_every_year=True
	else:
		split_every_year=False
	dates = split_date_range(d1,d2,days=days_per_chunk,split_at_year=split_every_year)
	data = pandas.DataFrame()
	for _d1,_d2 in dates:
		print("Date range: %s -> %s" % (_d1,_d2))
		_data = get_data(api_type=api_type,
				 group=group,
				 params=params,
				 loc=loc,
				 d1=_d1,
				 d2=_d2)
		data = pandas.concat([data,_data]).reset_index(drop=True)
	return data


def main():
	"""Main function
	"""
	print("Select API:")
	apis = datasets.api_type.unique()
	[print(i, apis[i]) for i in range(len(apis))]
	num_api = int(input(">"))
	selected = datasets.loc[datasets["api_type"]==apis[num_api]].reset_index(drop=True)
	
	print("Select parameters:")
	for i in range(len(selected.index)):
		print(i,selected.loc[i].short_string)

	while True:
		try:
			params = input(">")
			params_selected_list = params.split(",")
			params_ints = [int(param) for param in params_selected_list]
			p = selected.loc[params_ints[0]]
			params_ids = ",".join([selected.loc[params_ints[i]].id for i in range(len(params_selected_list))])
			param_names = ",".join([selected.loc[params_ints[i]].long_string for i in range(len(params_selected_list))])
			break
		except:
			print("Invalid parameters specified, please try again.")
			pass

	
	while True:
		try:
			d1 = dateparser.parse(input("Start date:\n"),date_formats=DATE_FORMATS)
			break
		except:
			print("Invalid date specified, please try again.")
			pass

	while True:
		try:
			d2 = dateparser.parse(input("End date:\n"),date_formats=DATE_FORMATS)
			break
		except:
			print("Invalid date specified, please try again.")
			pass

	d1 = d1.strftime("%Y-%m-%d")
	d2 = d2.strftime("%Y-%m-%d")

	locs = get_locations(d1,d2,p.type)
	for i in range(len(locs.index)):
		_l = locs.loc[i]
		print(i,_l.location_name,"("+_l.type_desc+")")
	
	while True:
		try:
			num_loc = int(input(">"))
			l = locs.loc[num_loc]
			break
		except:
			print("Invalid location specified, please try again.")
			pass

	data = get_data_nice(api_type=p.api_type,group=p.group,params=params_ids,loc=l.id,d1=d1,d2=d2)

	if data.shape[0] > 0:
		data_columns = [k for k in data.keys() if "data_" in k]
		data_ids = [p.replace("data_","") for p in data_columns]
		parameters = data.loc[0,"parameters"]
		data_headers = [parameters[p_id]["s"] for p_id in data_ids]
		data_print=data[["time"]+data_columns]
		rename_dict = {}
		for _col in data_columns:
			_id = _col.replace("data_","")
			rename_dict[_col] = parameters[_id]["s"]
		data_print.rename(columns=rename_dict,inplace=True)
		print(tabulate.tabulate(data_print,headers=["Time"]+data_headers,showindex=False))
		plot_data(data,param_names)
	else:
		print("No data from the selected station in the given time range!")
		exit()

	while True:
		_save = input("Save data? [y/n]\n>")
		if _save in ["y","n"]:
			break

	if _save == "y":
		_name = input("Please enter desired file name:\n>")
		data_print.to_excel(_name+".xlsx")
		print("File saved!")


main()