
from flask import Blueprint, jsonify
from models import Country,RealtimeCountryStats,DailyVaccineCountry,DailyCountryHistory
from flask import request
from sqlalchemy import desc,asc
from models import DailyCountryHistory
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)


@api_bp.route('/country/info')
def get_country_info():
    code = request.args.get('code', default='CN')  # 默认改成中国
    country = Country.query.filter_by(country_code=code.upper()).first()
    if not country:
        return jsonify({'error': 'Country not found'}), 404

    return jsonify({
        'country': country.country_name,
        'continent': country.continent,
        'latitude': country.latitude,
        'longitude': country.longitude,
        'flag_url': country.flag_url
    })

@api_bp.route('/country/stats')
def get_country_stats():
    code = request.args.get('code', default='CN')
    record = RealtimeCountryStats.query.filter_by(country_code=code.upper()).order_by(desc(RealtimeCountryStats.collected_at)).first()

    if not record:
        return jsonify({'error': 'No data for this country'}), 404

    return jsonify({
        'cases': record.cases,
        'active': record.active,
        'recovered': record.recovered,
        'deaths': record.deaths,
        'critical': record.critical,
        'tests': record.tests,
        'population': record.population,
        'updated_at': record.collected_at.strftime('%Y-%m-%d %H:%M')
    })

@api_bp.route('/vaccine/trend')
def get_vaccine_trend():
    code = request.args.get('code', default='CN')
    records = DailyVaccineCountry.query \
        .filter_by(country_code=code.upper()) \
        .order_by(DailyVaccineCountry.stat_date) \
        .all()

    result = {
        'dates': [r.stat_date.strftime('%Y-%m-%d') for r in records],
        'doses': [r.doses for r in records]
    }

    return jsonify(result)


@api_bp.route('/country/trend')
def get_country_trend():
    code = request.args.get('code', default='CN')
    start = request.args.get('start')
    end = request.args.get('end')

    query = DailyCountryHistory.query.filter_by(country_code=code.upper())
    if start and end:
        query = query.filter(DailyCountryHistory.stat_date.between(start, end))
    query = query.order_by(DailyCountryHistory.stat_date)

    records = query.all()

    result = {
        'dates': [r.stat_date.strftime('%Y-%m-%d') for r in records],
        'cases': [r.cases for r in records],
        'deaths': [r.deaths for r in records],
        'recovered': [r.recovered for r in records]
    }
    return jsonify(result)

def generate_future_dates(days, start_date=None):
    if start_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start = datetime.today()

    return [(start + timedelta(i)).strftime('%Y-%m-%d') for i in range(1, days + 1)]



def simulate_prediction(code, days):
    # 查询最近7天的数据
    recent = DailyCountryHistory.query \
        .filter_by(country_code=code.upper()) \
        .order_by(DailyCountryHistory.stat_date.desc()) \
        .limit(7).all()

    if len(recent) < 2:
        return [0] * days  # 不足2天数据时返回0

    # 倒序→正序，方便计算
    recent = list(reversed(recent))
    daily_cases = [r.cases for r in recent]

    # 计算日增数列表
    daily_increase = [
        daily_cases[i] - daily_cases[i - 1]
        for i in range(1, len(daily_cases))
    ]
    avg_increase = sum(daily_increase) // len(daily_increase)

    # 从最近最后一天开始预测
    last_known = daily_cases[-1]
    predictions = []
    for _ in range(days):
        last_known += avg_increase
        predictions.append(last_known)

    return predictions

@api_bp.route('/predict')
def predict():
    code = request.args.get('code', default='CN')
    days = int(request.args.get('days', 7))

    # 获取历史数据并做简单预测（例如线性外推）
    dates = generate_future_dates(days)
    predicted_cases = simulate_prediction(code, days)

    return jsonify({
        'dates': dates,
        'predicted_cases': predicted_cases
    })

