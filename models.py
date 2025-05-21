from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Country(db.Model):
    __tablename__ = 'country'
    country_code = db.Column(db.String(5), primary_key=True)
    country_name = db.Column(db.String(100))
    iso3 = db.Column(db.String(5))
    geo_id = db.Column(db.Integer)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    continent = db.Column(db.String(50))
    flag_url = db.Column(db.String(255))

class RealtimeCountryStats(db.Model):
    __tablename__ = 'realtime_country_stats'

    collected_at = db.Column(db.DateTime, primary_key=True)
    country_code = db.Column(db.String(5), primary_key=True)
    updated = db.Column(db.BigInteger)

    cases = db.Column(db.BigInteger)
    today_cases = db.Column(db.BigInteger)
    deaths = db.Column(db.BigInteger)
    today_deaths = db.Column(db.BigInteger)
    recovered = db.Column(db.BigInteger)
    today_recovered = db.Column(db.BigInteger)
    active = db.Column(db.BigInteger)
    critical = db.Column(db.BigInteger)
    tests = db.Column(db.BigInteger)
    population = db.Column(db.BigInteger)

class DailyVaccineCountry(db.Model):
    __tablename__ = 'daily_vaccine_country'
    stat_date = db.Column(db.Date, primary_key=True)
    country_code = db.Column(db.String(5), primary_key=True)
    doses = db.Column(db.BigInteger)

class DailyCountryHistory(db.Model):
    __tablename__ = 'daily_country_history'
    stat_date = db.Column(db.Date, primary_key=True)
    country_code = db.Column(db.String(5), primary_key=True)
    cases = db.Column(db.BigInteger)
    deaths = db.Column(db.BigInteger)
    recovered = db.Column(db.BigInteger)

class RealtimeGlobalStats(db.Model):
    __tablename__ = 'realtime_global_stats'

    collected_at = db.Column(db.DateTime, primary_key=True)  # ✅ 作为主键
    updated = db.Column(db.BigInteger)
    cases = db.Column(db.BigInteger)
    today_cases = db.Column(db.BigInteger)
    deaths = db.Column(db.BigInteger)
    today_deaths = db.Column(db.BigInteger)
    recovered = db.Column(db.BigInteger)
    today_recovered = db.Column(db.BigInteger)
    active = db.Column(db.BigInteger)
    critical = db.Column(db.BigInteger)
    tests = db.Column(db.BigInteger)
    population = db.Column(db.BigInteger)
    affected_countries = db.Column(db.Integer)

class ProvinceStat(db.Model):
    __tablename__ = 'province_stat'
    province_name = db.Column(db.String(50), primary_key=True)
    confirmed_count = db.Column(db.BigInteger)
    suspected_count = db.Column(db.BigInteger)
    cured_count = db.Column(db.BigInteger)
    dead_count = db.Column(db.BigInteger)
    update_time = db.Column(db.DateTime, primary_key=True)

class CityStat(db.Model):
    __tablename__ = 'city_stat'
    province_name = db.Column(db.String(50), primary_key=True)
    city_name = db.Column(db.String(50), primary_key=True)
    confirmed_count = db.Column(db.BigInteger)
    suspected_count = db.Column(db.BigInteger)
    cured_count = db.Column(db.BigInteger)
    dead_count = db.Column(db.BigInteger)
    update_time = db.Column(db.DateTime, primary_key=True)
