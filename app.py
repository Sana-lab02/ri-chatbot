from bot.RIbot import RetailBot
import pandas as pd
from flask import Flask, render_template, request, jsonify


bot = RetailBot()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    print("Flask: Received a request")
    user_input = request.json["message"]
    print("User input:", user_input)
    response = bot.process_input(user_input)
    print("Bot Response:", response)
    return jsonify({"reply": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

