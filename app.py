from flask import Flask, render_template
from config import SQLALCHEMY_DATABASE_URI
from models import db
from routes.api import api_bp

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)

app.register_blueprint(api_bp, url_prefix='/api')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/china')
def china():
    return render_template('china.html')


@app.route('/predict')
def predict_page():
    return render_template('predict.html')

@app.route('/china/province')
def china_province_detail():
    return render_template('province.html')

if __name__ == '__main__':
    app.run(debug=True)
