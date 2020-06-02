import flask
from flask import request

from main_code import parse

app= flask.Flask(__name__)
app.config["DEBUG"]=True

@app.route('/', methods=['POST', 'GET'])
def api_method():
    if request.is_json:
        return parse(request.get_json())
    else:
        print(request)
        return "Input not right"

app.run(host='127.0.0.1', port=8000)
