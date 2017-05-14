from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def index(request):
    context = {"title": "Home"}
    return JsonResponse(context)


@csrf_exempt
def create_model(request):
	if request.method == "POST":
		device_id = request.POST.get('device_id','')
		file = request.FILES['file']
		if file is not None and device_id != '':
			try:
				import boto3
				s3_resource = boto3.resource('s3')
				res = s3_resource.Object('userbehavior', device_id + '_3months.csv').put(Body=file)
				if res['ResponseMetadata']['HTTPStatusCode'] == 200:
					object_acl = s3_resource.ObjectAcl('userbehavior', device_id + '_3months.csv')
					object_acl.put(ACL='public-read')
					s3_url = "s3://userbehavior/" + device_id + '_3months.csv'
					result = model_create(device_id,s3_url)
					response = {"success":result}
					return JsonResponse(response)
				else:
					result = {'success': False, 'response': res}
					return JsonResponse(result)
			except Exception as e:
				response = {"error": e.value}
				return JsonResponse(response)
		else:
			response = {"error":"Empty parameters"}
			return JsonResponse(response)
	else:
		response = {"error":"Invalid HTTP method"}
		return JsonResponse(response)


def parser(x):
	from pandas import datetime
	return datetime.strptime(x, '%m/%d/%y %I:%M%p')


def model_create(device_id,s3_url):
	from pandas import read_csv
	from pandas import datetime
	import pandas as pd
	from statsmodels.tsa.arima_model import ARIMA
	from elasticsearch import Elasticsearch, RequestsHttpConnection
	import numpy as np
	from datetime import date
	from datetime import timedelta

	data = read_csv(s3_url, parse_dates=[0], index_col=0, squeeze=True,date_parser=parser)

	filtereddata = data[data['type'] != 'Missed']

	filtereddata = filtereddata[['number']]

	df = filtereddata.applymap(lambda x: str(x)[-10:])

	unique_number = df['number'].unique().tolist()

	selected_numbers = []
	for number in unique_number:
		df_number = df[df['number'] == number]
		res = df_number.groupby(pd.TimeGrouper('12H', closed='left')).agg(['count'])
		final_df = res['number']['count']
		final_df = final_df.astype('float')
		last_timestamp = final_df.tail(1).index[0]
		last_date = str(final_df.tail(1).index[0]).split(" ")[0]
		today = date.today()
		if str(today) != last_date:
			last_date_formatted = datetime.strptime(last_date, '%Y-%m-%d')
			today = datetime.strptime(str(today), '%Y-%m-%d')
			days_in_between = (today - last_date_formatted).days - 1
			values = np.zeros(days_in_between * 2)
			indices = []
			for i in range(0, days_in_between * 2):
				d = timedelta(hours=12)
				new_time = last_timestamp + d
				indices.append(new_time)
				last_timestamp = new_time
			new_series = pd.Series(values, index=indices)
			final_df = final_df.append(new_series)
		try:
			model = ARIMA(final_df, order=(5, 0, 2))
			output = model.fit(disp=-1)
			yhat = output.predict(final_df.size, final_df.size + 1)
			yhat = yhat[yhat > 0.5]
			if yhat.count() >= 1:
				selected_numbers.append(number)
		except:
			pass
	if len(selected_numbers)>0:
		today = date.today()
		es = Elasticsearch(hosts=[{'host': 'search-userbehavior-gwiellta5ffae4hj724yfvllpe.us-west-2.es.amazonaws.com', 'port': 443}],
						   use_ssl=True,verify_certs=True,connection_class=RequestsHttpConnection)
		doc = {
			'numbers': selected_numbers
		}
		res = es.index(index="predicted_numbers_"+device_id, doc_type=today, body=doc)
		return res['created']
	else:
		return True


@csrf_exempt
def daily_job(request):
	if request.method == "POST":
		device_id = request.POST.get('device_id', '')
		file = request.FILES['file']
		if file is not None and device_id != '':
			import boto3
			from datetime import date
			today = date.today()
			s3_resource = boto3.resource('s3')
			daily_file_name=device_id +'_'+str(today) +'.csv'
			res = s3_resource.Object('userbehavior', daily_file_name).put(Body=file)
			if res['ResponseMetadata']['HTTPStatusCode'] == 200:
				object_acl = s3_resource.ObjectAcl('userbehavior', daily_file_name)
				object_acl.put(ACL='public-read')
				s3_url = "s3://userbehavior/" + daily_file_name
				comparison_response=daily_comparison(s3_url,device_id)
				response=daily_append(s3_url,device_id)
				result={'comparison_response':comparison_response,'model_creation_trigger':response}
				return JsonResponse(result)
			else:
				result = {'success': False, 'response': res}
				return JsonResponse(result)

		else:
			response = {"error": "Empty parameters"}
			return JsonResponse(response)
	else:
		response = {"error": "Invalid HTTP method"}
		return JsonResponse(response)

def daily_comparison(s3_url,device_id):
	from pandas import read_csv
	from elasticsearch import Elasticsearch, RequestsHttpConnection
	import requests
	import json
	host = 'search-userbehavior-gwiellta5ffae4hj724yfvllpe.us-west-2.es.amazonaws.com'

	es = Elasticsearch(
		hosts=[{'host': host, 'port': 443}],
		use_ssl=True,
		verify_certs=True,
		connection_class=RequestsHttpConnection
	)
	if es.indices.exists(index="predicted_numbers_" + device_id):
		res = es.search(index="predicted_numbers_" + device_id, body={"query": {"match_all": {}}})

		for hit in res['hits']['hits']:
			predicted_number_array = set(hit["_source"]["numbers"])

		# read csv and compare csv with predicted number

		data = read_csv(s3_url, parse_dates=[0], index_col=0, squeeze=True, date_parser=parser)
		filtereddata = data[data['type'] != 'Missed']
		filtereddata = filtereddata[['number']]

		df = filtereddata.applymap(lambda x: str(x)[-10:])

		unique_number = set(df['number'].unique().tolist())

		predicted_number_not_found = list(predicted_number_array.difference(unique_number))


		es.indices.delete(index="predicted_numbers_" + device_id, ignore=[400, 404])

		if predicted_number_not_found:
			# send notification to onesignal
			header = {"Content-Type": "application/json; charset=utf-8",
					  "Authorization": "Basic NTVkNmQzOGQtMDM2OS00ODI0LWFmNzYtNDRjYWVkMmQ4NjNk"}

			print("send notification")
			data = {}
			data["numbers"] = predicted_number_not_found
			payload = {"app_id": 'f4c2e6f1-f386-4404-8c79-82c30fd156ac',
					   "include_player_ids": [device_id],
					   "contents": {"en": "You did not call today "},
					   "data": data
					   }

			req = requests.post("https://onesignal.com/api/v1/notifications", headers=header, data=json.dumps(payload))

			return {'status':req.status_code}
		else:
			return {'success':True}
	else:
		return {'success':False}


def daily_append(dailys3_url,device_id):
	from pandas import read_csv
	import pandas as pd
	from io import StringIO
	import boto3
	bigfile_url="s3://userbehavior/"+device_id+"_3months.csv"
	data = read_csv(bigfile_url)
	new_data=read_csv(dailys3_url)
	frames=[data,new_data]
	final_data=pd.concat(frames,ignore_index=True)
	csv_buffer = StringIO()
	final_data.to_csv(csv_buffer,index=False)
	s3_resource = boto3.resource('s3')
	res=s3_resource.Object('userbehavior', device_id+'_3months.csv').put(Body=csv_buffer.getvalue())
	if res['ResponseMetadata']['HTTPStatusCode']==200 :
		object_acl = s3_resource.ObjectAcl('userbehavior', device_id + '_3months.csv')
		object_acl.put(ACL='public-read')
		s3_url="s3://userbehavior/"+device_id+'_3months.csv'
		result=model_create(device_id, s3_url)
		return {'success':result}
	else:
		result={'success':False,'response':res}
		return result
