from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
  return "Som online bráško"

def run():
  app.run(host="0.0.0.0",port=9090)

def keep_alive():
  t = Thread(target=run)
  t.start()