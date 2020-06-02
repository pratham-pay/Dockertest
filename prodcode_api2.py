import json
import pandas as pd
from datetime import datetime
import re
import numpy as np
import flask
from flask import request

VALID_ACCOUNT_TYPES = {
    "1": "Personal Loan",
    "2": "Auto Loan"
}

def parse(json_obj):
    out_dict = {}

    for customer_id, account_list in json_obj.items():
        out_list = []

        if account_list and len(account_list) > 0:
            for account in account_list:
                parsed_account = parse_account(account)
                if parsed_account:
                    out_list.append(parsed_account)
            
        out_dict[customer_id] = out_list
    return out_dict

def get_nper(open_dt, bal_dt):
    nper = 12*(bal_dt.year-open_dt.year) + (bal_dt.month-open_dt.month) -1
    return nper

def parse_account(account):
    try:
        account_id = account['ACCOUNT_NB']
        account_type = account['ACCT_TYPE_CD']

        open_date = datetime.strptime(account['OPEN_DT'], "%Y/%m/%d")
        balance_dt = datetime.strptime(account['BALANCE_DT'], "%Y/%m/%d")
        amount = int(account['ORIG_LOAN_AM'])
    except:
        return None

    if account_type not in VALID_ACCOUNT_TYPES:
        return None

    total_paid_period = get_nper(open_date, balance_dt)

    p1 = re.compile('BALANCE_AM_\d{2}')
    bal_keys = sorted(list(filter(p1.match, account.keys())))

    p2 = re.compile('DAYS_PAST_DUE_\d{2}')
    dpd_keys = sorted(list(filter(p2.match, account.keys())))

    bal_array = []

    for b, d in zip(bal_keys, dpd_keys):
        
        if not pd.isna(account[d]) and account[d] == 0:
            bal = account[b]
            if not pd.isna(bal) and bal > 0 and bal < amount:
                per = total_paid_period - int(b[-2:]) + 1
                bal_array.append([bal, per])
    
    if len(bal_array) > 0:
        parsed_account = {}

        parsed_account['account_id'] = str(account_id)

        rate, tenure, emi = calc_emi(open_date, amount, bal_array)

        parsed_account['rate'] = float(rate)
        parsed_account['tenure'] = int(tenure)
        parsed_account['emi']= int(emi)
        
        return parsed_account
    else:
        return None


def calc_emi(open_date, amount, bal):
    np_rates = np.arange(10, 40, 0.5) 
    np_tenure = np.arange(1, 60, 1)
    
    rt_pairs = [(r,t) for r in np_rates for t in np_tenure]
    
    new_bal_array = []
    
    for tup in bal:
        balance = tup[0]
        nper = tup[1]
        
        new_bal_array.append((balance, nper))
    
    def multiproc(pair):
        r,t = pair
        nper_ = [1 if y>t else 0 for x,y in new_bal_array]
        
        if any(nper_) > 0:
            return None
        
        rate = r/1200
        emi = -np.pmt(rate, t, amount)
        diff=0

        for tup in new_bal_array:
            bal, nper = tup
            calc_balance = np.fv(rate, nper, emi, -amount)
            diff = diff+ (bal-calc_balance)**2

        balance_diff = np.sqrt(diff/len(new_bal_array))
        return balance_diff
    
    res = map(multiproc, rt_pairs)
    
    min_diff = float('inf')
    
    for tup, diff in zip(rt_pairs, res):
        if diff and diff < min_diff:
            min_diff = diff
            r,t=tup
    
    emi = -np.pmt(r/1200, t, amount)
    
    return (r,t,emi)
    

app= flask.Flask(__name__)
app.config["DEBUG"]=True

@app.route('/', methods=['POST'])
def api_method():
    if request.is_json:
        return parse(request.get_json())
    else:
        print(request)
        return "Input not right"

app.run(host='127.0.0.1', port=8080)
