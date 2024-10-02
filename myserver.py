from flask import Flask
from threading import Thread

app = False('')

@app.route('/')
def home():
    return "Server is runing"

def run():
    app.run(host='0.0.0.0',port=8000)

def server_on():
    t = Thread(target=run)
    t.start()