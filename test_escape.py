from flask import Flask, render_template_string

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string("""
    {% set myjson = '{"type": "quarter"}' %}
    <input value="{{ myjson }}">
    """)

with app.app_context():
    print(index())
