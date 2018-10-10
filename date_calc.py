from datetime import datetime
from datetime import timedelta

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


print(split_date_range("2018-01-01","2018-12-31",100))