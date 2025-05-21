
from flask import Blueprint, jsonify
from models import db,Country,RealtimeCountryStats,DailyVaccineCountry,RealtimeGlobalStats,CityStat,ProvinceStat
from flask import request
from sqlalchemy import desc,func
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


@api_bp.route('/china/province/stats')
def get_province_stats():
    # 获取最新日期
    latest = db.session.query(ProvinceStat.update_time).order_by(ProvinceStat.update_time.desc()).first()
    if not latest:
        return jsonify([])

    stats = (
        db.session.query(ProvinceStat)
        .filter(ProvinceStat.update_time == latest[0])
        .all()
    )

    return jsonify([
        {
            "province": s.province_name,
            "confirmed": s.confirmed_count,
            "cured": s.cured_count,
            "deaths": s.dead_count
        }
        for s in stats
    ])


@api_bp.route('/china/province/top5')
def get_top5_provinces():
    from models import ProvinceStat
    from sqlalchemy import func

    # 查找最新时间
    latest = (
        db.session.query(ProvinceStat.update_time)
        .order_by(ProvinceStat.update_time.desc())
        .first()
    )
    if not latest:
        return jsonify([])

    # 查找最新时间下的前5名
    top5 = (
        db.session.query(
            ProvinceStat.province_name,
            ProvinceStat.confirmed_count
        )
        .filter(ProvinceStat.update_time == latest[0])
        .order_by(ProvinceStat.confirmed_count.desc())
        .limit(5)
        .all()
    )

    return jsonify([
        {"province": row.province_name, "confirmed": row.confirmed_count}
        for row in top5
    ])


@api_bp.route('/china/cities')
def get_city_stats_by_province():
    province = request.args.get('province')
    if not province:
        return jsonify([])

    latest = (
        db.session.query(CityStat.update_time)
        .filter(CityStat.province_name == province)
        .order_by(CityStat.update_time.desc())
        .first()
    )

    if not latest:
        return jsonify([])

    stats = (
        db.session.query(CityStat)
        .filter(
            CityStat.province_name == province,
            CityStat.update_time == latest[0]
        )
        .all()
    )

    return jsonify([
        {
            "city": s.city_name,
            "confirmed": s.confirmed_count,
            "cured": s.cured_count,
            "deaths": s.dead_count
        }
        for s in stats
    ])

@api_bp.route('/china/province/trend')
def get_province_trend():
    province = request.args.get("province")
    start = request.args.get("start")
    end = request.args.get("end")

    if not (province and start and end):
        return jsonify({"error": "缺少参数"}), 400

    result = (
        db.session.query(
            CityStat.update_time,
            func.sum(CityStat.confirmed_count).label("cases"),
            func.sum(CityStat.cured_count).label("cured"),
            func.sum(CityStat.dead_count).label("deaths")
        )
        .filter(
            CityStat.province_name == province,
            CityStat.update_time >= start,
            CityStat.update_time <= end
        )
        .group_by(CityStat.update_time)
        .order_by(CityStat.update_time)
        .all()
    )

    return jsonify({
        "dates": [r.update_time.strftime('%Y-%m-%d') for r in result],
        "cases": [r.cases for r in result],
        "cured": [r.cured for r in result],
        "deaths": [r.deaths for r in result],
    })

@api_bp.route('/china/province/summary')
def get_province_summary():
    from models import ProvinceStat
    from sqlalchemy import func

    province = request.args.get("province")
    if not province:
        return jsonify({"error": "缺少省份参数"}), 400

    latest = (
        db.session.query(ProvinceStat.update_time)
        .filter(ProvinceStat.province_name == province)
        .order_by(ProvinceStat.update_time.desc())
        .first()
    )

    if not latest:
        return jsonify({})

    stat = (
        db.session.query(ProvinceStat)
        .filter(
            ProvinceStat.province_name == province,
            ProvinceStat.update_time == latest[0]
        )
        .first()
    )

    return jsonify({
        "confirmed": stat.confirmed_count,
        "suspected": stat.suspected_count,
        "recovered": stat.cured_count,
        "deaths": stat.dead_count,
        "date": stat.update_time.strftime('%Y-%m-%d')
    })
