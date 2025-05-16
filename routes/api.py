
from flask import Blueprint, jsonify
from models import Country,RealtimeCountryStats,DailyVaccineCountry,RealtimeGlobalStats
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

@api_bp.route('/global/growth-trend')
def global_growth_trend():
        records = RealtimeGlobalStats.query \
            .order_by(RealtimeGlobalStats.collected_at) \
            .limit(14).all()

        result = {'dates': [], 'rates': []}
        for r in records:
            if r.cases and r.today_cases:
                base = r.cases - r.today_cases
                rate = r.today_cases / base if base > 0 else 0
                result['dates'].append(r.collected_at.strftime('%Y-%m-%d'))
                result['rates'].append(rate)

        return jsonify(result)

@api_bp.route('/global/rt')
def get_global_rt():
    records = RealtimeGlobalStats.query.order_by(RealtimeGlobalStats.collected_at).limit(14).all()

    dates = []
    rts = []

    for i in range(3, len(records)):
        current = records[i]
        window = records[i-3:i]  # 前 3 天的活跃病例
        if current.today_cases and all(w.active for w in window):
            avg_active = sum(w.active for w in window) / 3
            rt = current.today_cases / avg_active if avg_active > 0 else 0
            dates.append(current.collected_at.strftime('%Y-%m-%d'))
            rts.append(round(rt, 4))

    return jsonify({'dates': dates, 'rt_values': rts})

@api_bp.route('/global/cfr')
def get_global_cfr():
    records = RealtimeGlobalStats.query.order_by(RealtimeGlobalStats.collected_at.desc()).limit(7).all()
    records.reverse()

    result = {
        'dates': [],
        'cfr_values': []
    }

    for r in records:
        cfr = (r.deaths / r.cases) if r.cases else 0
        result['dates'].append(r.collected_at.strftime('%Y-%m-%d'))
        result['cfr_values'].append(round(cfr * 100, 2))

    return jsonify(result)

@api_bp.route('/china/growth-trend')
def china_growth_trend():
    records = RealtimeCountryStats.query \
        .filter_by(country_code='CN') \
        .order_by(RealtimeCountryStats.collected_at) \
        .limit(14).all()

    result = {'dates': [], 'rates': []}
    for r in records:
        if r.cases and r.today_cases:
            base = r.cases - r.today_cases
            rate = r.today_cases / base if base > 0 else 0
            result['dates'].append(r.collected_at.strftime('%Y-%m-%d'))
            result['rates'].append(rate)

    return jsonify(result)

@api_bp.route('/china/rt')
def get_china_rt():
    records = RealtimeCountryStats.query \
        .filter_by(country_code='CN') \
        .order_by(RealtimeCountryStats.collected_at) \
        .limit(14).all()

    dates = []
    rts = []

    for i in range(3, len(records)):
        current = records[i]
        window = records[i-3:i]  # 前3天的活跃病例
        if current.today_cases and all(w.active for w in window):
            avg_active = sum(w.active for w in window) / 3
            rt = current.today_cases / avg_active if avg_active > 0 else 0
            dates.append(current.collected_at.strftime('%Y-%m-%d'))
            rts.append(round(rt, 4))

    return jsonify({'dates': dates, 'rt_values': rts})

@api_bp.route('/china/cfr')
def get_china_cfr():
    records = RealtimeCountryStats.query \
        .filter_by(country_code='CN') \
        .order_by(RealtimeCountryStats.collected_at.desc()) \
        .limit(7).all()
    records.reverse()

    result = {
        'dates': [],
        'cfr_values': []
    }

    for r in records:
        cfr = (r.deaths / r.cases) if r.cases else 0
        result['dates'].append(r.collected_at.strftime('%Y-%m-%d'))
        result['cfr_values'].append(round(cfr * 100, 2))

    return jsonify(result)