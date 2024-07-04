#Importing required libraries
from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import concurrent.futures
import time
import json

#Initializing Flask app
app = Flask(__name__)
import socket
import pandas as pd


# API endpoint information
	#Endpoint for Lambda function Warmup
ENDPOINT = "https://2mtqll3rue.execute-api.us-east-1.amazonaws.com"
FUNCTION_PATH = "/default/CClambda"
	#Endpoint for AWS EC2 connection using AWS Lambda
ENDPOINT_AWS = "https://10eoktg2b5.execute-api.us-east-1.amazonaws.com"
FUNCTION_PATH_AWS = "/default/ccec2connection"


	
# Warm-up API end point
@app.route('/warmup', methods=['GET', 'POST'])
def lambda_warmup():
	## Functionality for Lambda warm-up
    if request.method == 'POST':
        data = request.get_json()
        global ser
        global time_for_warm
        global warmm
        global num_resources
        global cost_warmup
        time_for_warmup = []
        
        if data['s'] == 'lambda':
            warmm = []
            num_resources = int(data['r'])
            ser = 'lambda'
            print(num_resources)
            
            def invoke_lambda_function(_):
                try:
                    start = time.time()
                    response = requests.post(ENDPOINT + FUNCTION_PATH)
                    response.raise_for_status()
                    print(f"Invoked Lambda function: {response.status_code}")
                    print("Elapsed Time:", time.time() - start)
                    time_for_warmup.append(time.time() - start)
                    warmm.append(response)
                except Exception as e:
                    print(f"Error invoking Lambda function: {e}")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(invoke_lambda_function, range(num_resources))
            print(time_for_warmup)
            time_for_warm = sum(time_for_warmup)
            print(time_for_warm)
            cost_warmup = str((time_for_warm / 60) * 0.0134)
            
            return jsonify({"result": "ok"})
        
        elif data['s'] == 'ec2':
            num_resources = int(data['r'])
            print(data)
            body = json.dumps({"num_resources": num_resources})
            headers = {'Content-Type': 'application/json'}
            warmm = []
            ser = 'ec2'
            
            
            def launch_ec2():
                try:
                    start = time.time()
                    response = requests.post(ENDPOINT_AWS + FUNCTION_PATH_AWS, headers=headers, data=body, verify=True)
                    time.sleep(10)
                    print(response)
                    data = response.json()
                    if response.status_code == 200:
                        warmm.append(data)
                    else:
                        return "Error invoking EC2"
                    print("Elapsed Time:", time.time() - start)
                    time_for_warmup.append(time.time() - start)
                    print(f"Invoked EC2")
                except Exception as e:
                    print(f"Error invoking EC2 function: {e}")

            launch_ec2()
            time_for_warm = sum(time_for_warmup)
            print(time_for_warm)
            cost_warmup = str((time_for_warm / 3600) * num_resources * 0.012)
            
            return jsonify({"result": "ok"})



# API endpoint for checking whether resources are warmedup or not
@app.route('/scaled_ready', methods=['GET', 'POST'])
def resources_ready():
	## Functionality for checking resources status
    if request.method == 'GET':
        if ser == "ec2":
            if num_resources == len(warmm[0]):
                print(warmm)
                print(num_resources)
                return jsonify({"warm": True})
            else:
                print(warmm)
                print(num_resources)
                return jsonify({"warm": False})
        else:
            if num_resources == len(warmm):
                print(warmm)
                print(num_resources)
                return jsonify({"warm": True})
            else:
                print(warmm)
                print(num_resources)
                return jsonify({"warm": False})



# API endpoint to get warmup cost
@app.route('/get_warmup_cost', methods=['GET', 'POST'])     
def get_warmup_cost():
	# Functionality for retrieving warm-up cost
    if request.method == 'GET':
        return {"billable_time": time_for_warm, "cost": cost_warmup}
    
   	
     
#API endpoint to get resources endpoints information
@app.route('/get_endpoints', methods=['GET', 'POST'])     
def get_endpoints():
# Functionality for retrieving resources endpoints information
    if request.method == 'GET':
        dns_list = []
        r = {}
        if ser == "ec2":
            for i in warmm:
                for j in i:
                    if 'PublicDnsName' in j:
                        dns_list.append("http://" + str(j['PublicDnsName']) + "/")
            for i in range(len(dns_list)):
                r[f"resource {i}"] = dns_list[i]
            return r
        else:
            x = "There are no endpoints for Lambda."
            return x
 
#API to analyse 
 # Functionality for data analysis
@app.route('/analyse', methods=['GET', 'POST'])
def analyse():
    if request.method == 'POST':
        data = request.get_json()  # Handles data from a JSON body cURL request
        if not data or not all(k in data for k in ('h', 'd', 't', 'p')):
            return jsonify({"error": "Missing one or more of the required data parameters"}), 400

        # Extracting variables from JSON data
        h = int(data['h'])
        d = int(data['d'])
        buysell = str(data['t'])
        if buysell == "buy":
            t = "1"
        else:
            t = "0"
        p = int(data['p'])
        body = json.dumps({"minhistory": h, "shots": d, "bs": t, "profit_loss_days": p})
        da = {"minhistory": h, "shots": d, "bs": t, "profit_loss": p}
        global responses
        global time_for_analysis
        global cost_analysis
        global val_95
        global val_99
        global avg_95
        global avg_99
        global total_billable_time
        global total_cost
        responses = []
        global sorted_responses
        global sum_of_pl
        if ser == "lambda":
            start = time.time()

            def invoke_lambda_function(_):
                try:
                    response = requests.post(ENDPOINT + FUNCTION_PATH, data=body, verify=False)
                    print(response.json())
                    return response.json()
                except Exception as e:
                    print(f"Error invoking Lambda function: {e}")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                responses = list(executor.map(invoke_lambda_function, range(num_resources)))
            time_for_analysis = time.time() - start
            cost_analysis = str((time_for_analysis / 60) * 0.0134)

        if ser == "ec2":
            url = []
            ips = []
            start = time.time()
            headers = {'Content-Type': 'application/json'}
            for i in warmm:
                for j in i:
                    if 'PublicIpAddress' in j:
                        ips.append(j['PublicIpAddress'])
                        url.append("http://" + j['PublicIpAddress'] + ":80")
            print(url)
            for i in ips:
                if check_connection(i) == 1:
                    print("connected")
                    time.sleep(10)
                    connect = "http://" + i + ":80"
                    response = requests.post(connect, headers=headers, json=da, verify=True, timeout=600)
                    responses.append(response.json())
            time_for_analysis = time.time() - start
            cost_analysis = str((time_for_analysis / 3600) * num_resources * 0.012)

        # sorting responses for  get_sig_vars9599 & get_sig_profit_loss api endpoints
        data_list = [response["data"] for response in responses]
        flattened_data = [item for sublist in data_list for item in sublist]
        sorted_responses = sorted(flattened_data, key=lambda x: x['date'])

        print(sorted_responses)

        val_95 = []
        val_99 = []

        # Calculating Averages for the avg api endpoints 
        for j in flattened_data:
            val_95.append(j["95%"])
            val_99.append(j["99%"])
        avg_95 = sum(val_95) / len(val_95)
        avg_99 = sum(val_99) / len(val_99)

        # Calculating total profit
        pl_values = []
        for j in flattened_data:
            pl_values.append(j["Profit/Loss"])
        sum_of_pl = sum(pl_values)

        # Calculating total costs
        total_billable_time = time_for_warm + time_for_analysis
        cw = cost_warmup
        total_cost = float(cw) + float(cost_analysis)

        # Storing Audit Data to data.json via AWS Lambda function
        headers = {'Content-Type': 'application/json'}
        data = {"ser": ser, "num_resources": num_resources, "h": h, "d": d, "t": t, "p": p,
                "sum_of_pl": sum_of_pl, "avg_95": avg_95, "avg_99": avg_99,
                "total_billable_time": total_billable_time, "total_cost": total_cost}
        body = json.dumps(data)
        response = requests.post("https://08w8thvjud.execute-api.us-east-1.amazonaws.com/default/CCaudit",
                                 headers=headers, data=body, verify=True, timeout=600)

        return {"result": "ok"}

# Function for checking EC2 connection
def check_connection(ip):
    retries = 10
    retry_delay = 10
    retry_count = 0
    while retry_count <= retries:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        time.sleep(10)
        result = sock.connect_ex((ip, 80))
        if result == 0:
            print("Instance is UP & accessible on port 80")
            return 1
        else:
            print("instance is still down retrying . . . ")
            return (check_connection(ip))

# API endpoint for getting first 20 values for var95 & var99 on the basis of date 
@app.route('/get_sig_vars9599', methods=['GET', 'POST'])
def get_sig_vars9599():
    if request.method == 'GET':
        if sorted_responses is None:
            return "Data has been reset, please run the analysis again."
        
        # Select the first 20 dictionaries
        first_20_by_date = sorted_responses[:20]
        
        response_data = {"var95": [], "var99": []}

        for i in first_20_by_date:
            response_data["var95"].append(i["95%"])
            response_data["var99"].append(i["99%"])

        return response_data
        
# API endpoint for average values for var95 & var99          
@app.route('/get_avg_vars9599', methods=['GET', 'POST'])     
def get_avg_vars9599():
    if request.method == 'GET':
        if avg_95 is None and avg_99 is None:
            return "Data has been reset, please run the analysis again."
        return {"var95": avg_95, "var99": avg_99}
    
        
# API endpoint for getting last 20 values for Profit/Loss on the basis of date
@app.route('/get_sig_profit_loss', methods=['GET', 'POST'])     
def get_sig_profit_loss():
    if request.method == 'GET':
        if sorted_responses is None:
            return "Data has been reset, please run the analysis again."
        response_data = {"profit_loss": []}
        last_20_by_date = sorted_responses[-20:]
        for i in last_20_by_date:
            response_data["profit_loss"].append(i["Profit/Loss"])
        return response_data
    
# API endpoint for getting total profit        
@app.route('/get_tot_profit_loss', methods=['GET', 'POST'])
def get_tot_profit_loss():
    if request.method == 'GET':
        if sum_of_pl is None:
            return "Data has been reset, please run the analysis again."
        return {"profit_loss": sum_of_pl}
    
# API endpoint for getting a chart based on the responses  
@app.route('/get_chart_url', methods=['GET', 'POST'])
def get_chart_url():
    if request.method == 'GET':
        var95 = []
        var99 = []
        dates = []
        global chart
        if responses is None:
            return "Data has been reset, please run the analysis again."
        data_list = [response["data"] for response in responses]
        flattened_data = [item for sublist in data_list for item in sublist]
        for j in flattened_data:
            var95.append(j["95%"])
            var99.append(j["99%"])
            dates.append(j["date"])
        var95_avg = sum(var95) / len(var95)
        var99_avg = sum(var99) / len(var99)

        var95_avgd = [var95_avg] * len(var95)
        var99_avgd = [var99_avg] * len(var99)
            
        note = list(zip(dates, var95_avgd, var99_avgd))
            
        str_d = '|'.join(dates)
        str_95 = ','.join([str(i) for i in var95])
        str_avg95 = ','.join([str(var95_avg) for i in range(len(dates))])
        str_99 = ','.join([str(i) for i in var99])
        str_avg99 = ','.join([str(var99_avg) for i in range(len(dates))])
        labels = "95%RiskValue|99%RiskValue|Average95%|Average99%"
            
        chart = f"https://image-charts.com/chart?cht=lc&chs=999x499&chd=a:{str_95}|{str_99}|{str_avg95}|{str_avg99}&chxt=x,y&chdl={labels}&chxl=0:|{

str_d}&chxs=0,min90&chco=1984C5,C23728,A7D5ED,E1A692&chls=3|3|3,5,3|3,5,3"
        
        return {"url": chart}

 
# API endpoint to get total billable time and cost
@app.route('/get_time_cost', methods=['GET', 'POST'])
def get_time_cost():
    if request.method == 'GET':
        if total_billable_time is not None and total_cost is not None:
            return {"time": total_billable_time, "cost": total_cost}
        else:
            return "Data has been reset, please run the analysis again."
       

# API endpoint for getting Audit data   
@app.route('/get_audit', methods=['GET', 'POST'])
def get_audit():
    
    if request.method == 'GET':
        global r_audit
        res_get=requests.post("https://ab7s9qld6a.execute-api.us-east-1.amazonaws.com/default/ccshowdata")
        r_audit=res_get.json()
        print(r_audit)
        return r_audit
    
# API endpoint for resetting the stored values            
@app.route('/reset', methods=['GET', 'POST'])
def reset():
    if request.method == 'GET':
        global time_for_warm, warmm, num_resources, h, d, t, p, sum_of_pl, avg_95, avg_99, total_billable_time, total_cost, cost_warmup, time_for_analysis, sorted_responses, responses, cost_analysis, r_audit
        
        time_for_warm = None
        num_resources = None
        h = None
        d = None
        t = None
        p = None
        sum_of_pl = None
        avg_95 = None
        avg_99 = None
        total_billable_time = None
        total_cost = None
        cost_warmup = None
        sorted_responses = None
        responses = None
        time_for_analysis = None
        cost_analysis = None
        r_audit = None
        return {"result": "ok"}
        

# API endpoint for terminating all the running resources
@app.route('/terminate', methods=['GET', 'POST'])
def terminate():
    if request.method == 'GET':
        global terminated
        headers = {'Content-Type': 'application/json'}
        instances_running = []
        print(warmm)
        if ser == "ec2":
            for i in warmm:
                for j in i:
                    if 'InstanceId' in j:
                        instances_running.append(j['InstanceId'])
                    else:
                        return {"terminated": "true"}
            instances_running = str(instances_running)
            body = json.dumps({"instances": instances_running})
            response = requests.post(" https://tplba7ox2h.execute-api.us-east-1.amazonaws.com/default/ccterminate", headers=headers, data=body, verify=True)
            r = response.json()
            if "ResponseMetadata" in r:
                terminated = "ok"
                return {"result": "ok"}
          
        if ser == "lambda":
            terminated = "ok"
            return {"result": "ok"}
            
# API endpoint for checking the resources has been terminated or not        
@app.route('/scaled_terminated', methods=['GET', 'POST'])
def resources_terminated():
    if request.method == 'GET':
        if terminated == "ok":
            return {"terminated": "true"}
        else:
            return {"terminated": "false"}
    

if __name__ == '__main__':
    app.run()

