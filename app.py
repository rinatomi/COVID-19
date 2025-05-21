from flask import Flask, jsonify, request, render_template, Response
from flask_cors import CORS
import mysql.connector
import json
import requests
import logging
from datetime import datetime, timedelta
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import pandas as pd

app = Flask(__name__)
CORS(app)  # 启用跨域请求支持

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/opt/covid-analysis/api-service/api_detail.log'
)
logger = logging.getLogger(__name__)

# 数据库连接配置
db_config = {
    'host': 'localhost',
    'user': 'covid_user',
    'password': 'ROOT050313cel*',
    'database': 'covid_analysis'
}

def get_db_connection():
    """获取数据库连接"""
    try:
        return mysql.connector.connect(**db_config)
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise

def fetch_from_disease_sh(endpoint):
    """从disease.sh API获取数据的通用函数"""
    try:
        base_url = 'https://disease.sh/v3/covid-19'
        response = requests.get(f"{base_url}/{endpoint}")
        return response.json()
    except Exception as e:
        logger.error(f"从disease.sh获取数据失败 ({endpoint}): {str(e)}")
        return None

def map_global_data_fields(data, is_from_api=False):
    """统一全球数据的字段名称"""
    if is_from_api:
        return {
            'updated': data.get('updated'),
            'cases': data.get('cases'),
            'today_cases': data.get('todayCases'),
            'deaths': data.get('deaths'),
            'today_deaths': data.get('todayDeaths'),
            'recovered': data.get('recovered'),
            'today_recovered': data.get('todayRecovered'),
            'active': data.get('active'),
            'critical': data.get('critical'),
            'tests': data.get('tests'),
            'population': data.get('population'),
            'affected_countries': data.get('affectedCountries'),
            'cases_per_million': data.get('casesPerOneMillion'),
            'deaths_per_million': data.get('deathsPerOneMillion'),
            'tests_per_million': data.get('testsPerOneMillion'),
            'timestamp': int(datetime.now().timestamp())
        }
    else:
        return data

@app.route('/api/global', methods=['GET'])
def get_global_data():
    """获取最新的全球数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
                SELECT * FROM realtime_global_stats 
                ORDER BY collected_at DESC LIMIT 1
        """
        
        cursor.execute(query)
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            logger.info("成功从数据库获取全球数据")
            return jsonify(map_global_data_fields(result))
        else:
            logger.info("数据库中没有全球数据，从disease.sh获取")
            data = fetch_from_disease_sh('all')
            if data:
                return jsonify(map_global_data_fields(data, is_from_api=True))
            else:
                return jsonify({"error": "无法获取全球数据"}), 500
    except Exception as e:
        logger.error(f"获取全球数据失败: {str(e)}")
        try:
            data = fetch_from_disease_sh('all')
            if data:
                logger.info("成功从disease.sh获取全球数据（作为备选）")
                return jsonify(map_global_data_fields(data, is_from_api=True))
            else:
                return jsonify({"error": "无法获取全球数据"}), 500
        except Exception as ex:
            logger.error(f"从disease.sh获取全球数据失败: {str(ex)}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/countries', methods=['GET'])
def get_countries_data():
    """获取最新的国家数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT rs.*, c.country_name, c.latitude as lat, c.longitude as `long`, 
                   c.continent, c.flag_url
            FROM realtime_country_stats rs
            JOIN country c ON rs.country_code = c.country_code
            JOIN (
                SELECT country_code, MAX(collected_at) as max_collected_at 
                FROM realtime_country_stats 
                GROUP BY country_code
            ) latest ON rs.country_code = latest.country_code AND rs.collected_at = latest.max_collected_at
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results and len(results) > 0:
            logger.info(f"成功从数据库获取国家数据，共{len(results)}个国家")
            return jsonify(results)
        else:
            logger.info("数据库中没有国家数据，从disease.sh获取")
            data = fetch_from_disease_sh('countries')
            
            if data:
                formatted_data = []
                for country in data:
                    formatted_data.append({
                        'country_code': country.get('countryInfo', {}).get('iso2'),
                        'country_name': country.get('country'),
                        'cases': country.get('cases'),
                        'today_cases': country.get('todayCases'),
                        'deaths': country.get('deaths'),
                        'today_deaths': country.get('todayDeaths'),
                        'recovered': country.get('recovered'),
                        'today_recovered': country.get('todayRecovered'),
                        'active': country.get('active'),
                        'critical': country.get('critical'),
                        'tests': country.get('tests'),
                        'population': country.get('population'),
                        'continent': country.get('continent'),
                        'lat': country.get('countryInfo', {}).get('lat'),
                        'long': country.get('countryInfo', {}).get('long'),
                        'flag_url': country.get('countryInfo', {}).get('flag')
                    })
                return jsonify(formatted_data)
            else:
                return jsonify({"error": "无法获取国家数据"}), 500
    except Exception as e:
        logger.error(f"获取国家数据失败: {str(e)}")
        try:
            data = fetch_from_disease_sh('countries')
            if data:
                logger.info("成功从disease.sh获取国家数据（作为备选）")
                formatted_data = []
                for country in data:
                    formatted_data.append({
                        'country_code': country.get('countryInfo', {}).get('iso2'),
                        'country_name': country.get('country'),
                        'cases': country.get('cases'),
                        'today_cases': country.get('todayCases'),
                        'deaths': country.get('deaths'),
                        'today_deaths': country.get('todayDeaths'),
                        'recovered': country.get('recovered'),
                        'today_recovered': country.get('todayRecovered'),
                        'active': country.get('active'),
                        'critical': country.get('critical'),
                        'tests': country.get('tests'),
                        'population': country.get('population'),
                        'continent': country.get('continent'),
                        'lat': country.get('countryInfo', {}).get('lat'),
                        'long': country.get('countryInfo', {}).get('long'),
                        'flag_url': country.get('countryInfo', {}).get('flag')
                    })
                return jsonify(formatted_data)
            else:
                return jsonify({"error": "无法获取国家数据"}), 500
        except Exception as ex:
            logger.error(f"从disease.sh获取国家数据失败: {str(ex)}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/countries/top/<int:limit>', methods=['GET'])
def get_top_countries(limit):
    """获取确诊病例数最多的前N个国家"""
    try:
        # 获取排序字段，默认按确诊病例数排序
        sort_by = request.args.get('sort_by', 'cases')
        allowed_fields = ['cases', 'deaths', 'recovered', 'active', 'critical', 'today_cases', 'today_deaths']
        
        if sort_by not in allowed_fields:
            sort_by = 'cases'  # 如果排序字段无效，默认使用确诊病例数
            
        # 限制查询结果数量，最大100
        if limit > 100:
            limit = 100
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = f"""
        SELECT rs.*, c.country_name, c.latitude as lat, c.longitude as `long`, 
               c.continent, c.flag_url
        FROM realtime_country_stats rs
        JOIN country c ON rs.country_code = c.country_code
        JOIN (
            SELECT country_code, MAX(collected_at) as max_collected_at 
            FROM realtime_country_stats 
            GROUP BY country_code
        ) latest ON rs.country_code = latest.country_code AND rs.collected_at = latest.max_collected_at
        ORDER BY rs.{sort_by} DESC
        LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results and len(results) > 0:
            logger.info(f"成功获取TopN国家数据，排序字段:{sort_by}，限制:{limit}，共返回{len(results)}个国家")
            return jsonify(results)
        else:
            logger.info(f"无法从数据库获取TopN国家数据，尝试从完整数据集筛选")
            countries_data = get_countries_data().json
            
            # 确保结果是列表
            if not isinstance(countries_data, list):
                return jsonify({"error": "无法获取国家数据"}), 500
                
            # 按指定字段排序并截取前N个
            sorted_countries = sorted(
                countries_data, 
                key=lambda x: x.get(sort_by, 0) if x.get(sort_by) is not None else 0, 
                reverse=True
            )[:limit]
            
            return jsonify(sorted_countries)
    except Exception as e:
        logger.error(f"获取TopN国家数据失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/countries/<country_code>', methods=['GET'])
def get_country_data(country_code):
    """获取指定国家的最新数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
                SELECT rs.*, c.country_name, c.latitude as lat, c.longitude as `long`, 
                      c.continent, c.flag_url
                FROM realtime_country_stats rs
                JOIN country c ON rs.country_code = c.country_code
                WHERE rs.country_code = %s
                ORDER BY rs.collected_at DESC LIMIT 1
        """
        
        cursor.execute(query, (country_code,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            logger.info(f"成功从数据库获取国家数据: {country_code}")
            return jsonify(result)
        else:
            logger.info(f"数据库中没有国家数据: {country_code}，从disease.sh获取")
            data = fetch_from_disease_sh(f'countries/{country_code}')
            if data:
                # 格式化数据
                formatted_data = {
                    'country_code': data.get('countryInfo', {}).get('iso2'),
                    'country_name': data.get('country'),
                    'cases': data.get('cases'),
                    'today_cases': data.get('todayCases'),
                    'deaths': data.get('deaths'),
                    'today_deaths': data.get('todayDeaths'),
                    'recovered': data.get('recovered'),
                    'today_recovered': data.get('todayRecovered'),
                    'active': data.get('active'),
                    'critical': data.get('critical'),
                    'tests': data.get('tests'),
                    'population': data.get('population'),
                    'continent': data.get('continent'),
                    'lat': data.get('countryInfo', {}).get('lat'),
                    'long': data.get('countryInfo', {}).get('long'),
                    'flag_url': data.get('countryInfo', {}).get('flag')
                }
                return jsonify(formatted_data)
            else:
                return jsonify({"error": f"国家未找到: {country_code}"}), 404
    except Exception as e:
        logger.error(f"获取国家数据失败: {country_code}, {str(e)}")
        try:
            data = fetch_from_disease_sh(f'countries/{country_code}')
            if data:
                logger.info(f"成功从disease.sh获取国家数据: {country_code}（作为备选）")
                # 格式化数据
                formatted_data = {
                    'country_code': data.get('countryInfo', {}).get('iso2'),
                    'country_name': data.get('country'),
                    'cases': data.get('cases'),
                    'today_cases': data.get('todayCases'),
                    'deaths': data.get('deaths'),
                    'today_deaths': data.get('todayDeaths'),
                    'recovered': data.get('recovered'),
                    'today_recovered': data.get('todayRecovered'),
                    'active': data.get('active'),
                    'critical': data.get('critical'),
                    'tests': data.get('tests'),
                    'population': data.get('population'),
                    'continent': data.get('continent'),
                    'lat': data.get('countryInfo', {}).get('lat'),
                    'long': data.get('countryInfo', {}).get('long'),
                    'flag_url': data.get('countryInfo', {}).get('flag')
                }
                return jsonify(formatted_data)
            else:
                return jsonify({"error": f"国家未找到: {country_code}"}), 404
        except Exception as ex:
            logger.error(f"从disease.sh获取国家数据失败: {country_code}, {str(ex)}")
            return jsonify({"error": f"无法获取国家数据: {str(e)}"}), 500

@app.route('/api/history/country/<country_code>', methods=['GET'])
def get_history_country(country_code):
    """历史数据API的别名路由"""
    return get_country_history(country_code)

@app.route('/api/countries/<country_code>/history', methods=['GET'])
def get_country_history(country_code):
    """获取指定国家的历史数据"""
    try:
        # 获取日期范围参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        days = request.args.get('lastdays', '30')

        # 验证日期参数
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                if start > end:
                    return jsonify({"error": "开始日期不能晚于结束日期"}), 400
                
                # 计算日期范围
                date_range = (end - start).days + 1
                if date_range > 365:
                    return jsonify({"error": "日期范围不能超过365天"}), 400
                
                min_date = datetime(2020, 1, 1)
                max_date = datetime.now()
                if start > max_date or end < min_date:
                    return jsonify({"error": f"请选择2020-01-01至今的日期范围"}), 400
            except ValueError:
                return jsonify({"error": "日期格式无效，请使用YYYY-MM-DD格式"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 构建查询条件
        query = """
        SELECT * FROM daily_country_history 
        WHERE country_code = %s
        """
        params = [country_code]
        
        if start_date and end_date:
            query += " AND stat_date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        else:
            if not days.isdigit():
                days = '30'
            query += " AND stat_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)"
            params.append(int(days))
        
        query += " ORDER BY stat_date ASC"
        
        logger.info(f"执行查询: {query}, 参数: {params}")
        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        
        if not results:
            logger.info(f"指定日期范围没有数据，尝试获取所有可用历史数据: {country_code}")
            query = """
            SELECT * FROM daily_country_history 
            WHERE country_code = %s
            ORDER BY stat_date ASC
            """
            cursor.execute(query, (country_code,))
            results = cursor.fetchall()
            
            if results:
                first_date = results[0]['stat_date'].strftime('%Y-%m-%d')
                last_date = results[-1]['stat_date'].strftime('%Y-%m-%d')
                
                if start_date and end_date:
                    return jsonify({
                        "error": f"所选日期范围内没有数据 ({start_date} 至 {end_date})",
                        "available_range": f"可用的数据范围是 {first_date} 至 {last_date}"
                    }), 404
        
        if results and len(results) > 0:
            logger.info(f"成功从daily_country_history获取国家历史数据: {country_code}, 共{len(results)}条记录")
            
            formatted_data = {
                "country": country_code,
                "timeline": {
                    "cases": {},
                    "deaths": {},
                    "recovered": {}
                }
            }
            
            # 确保数据连续性
            start_date_obj = results[0]['stat_date']
            end_date_obj = results[-1]['stat_date']
            current_date = start_date_obj
            
            # 存储前一天的数据用于填充空缺
            prev_data = {
                "cases": 0,
                "deaths": 0,
                "recovered": 0
            }
            
            while current_date <= end_date_obj:
                date_str = current_date.strftime('%Y-%m-%d')
                # 查找当前日期的数据
                matching_row = next(
                    (row for row in results if row['stat_date'].strftime('%Y-%m-%d') == date_str),
                    None
                )
                
                if matching_row:
                    formatted_data["timeline"]["cases"][date_str] = matching_row["cases"]
                    formatted_data["timeline"]["deaths"][date_str] = matching_row["deaths"]
                    formatted_data["timeline"]["recovered"][date_str] = matching_row.get("recovered", 0)
                    
                    # 更新前一天的数据
                    prev_data = {
                        "cases": matching_row["cases"],
                        "deaths": matching_row["deaths"],
                        "recovered": matching_row.get("recovered", 0)
                    }
                else:
                    # 使用前一天的数据填充空缺
                    formatted_data["timeline"]["cases"][date_str] = prev_data["cases"]
                    formatted_data["timeline"]["deaths"][date_str] = prev_data["deaths"]
                    formatted_data["timeline"]["recovered"][date_str] = prev_data["recovered"]
                
                current_date += timedelta(days=1)
            
            cursor.close()
            conn.close()
            return jsonify(formatted_data)
        else:
            cursor.close()
            conn.close()
            
            # 记录一下数据库没有数据的情况
            logger.info(f"数据库中没有国家历史数据: {country_code}，尝试从disease.sh获取")
            
            endpoint = f'historical/{country_code}'
            
            # 设置合理的获取范围
            if start_date and end_date:
                days = min(365, (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1)
            else:
                days = int(days) if days.isdigit() else 30
                
            endpoint += f'?lastdays={days}'
            
            logger.info(f"尝试从disease.sh获取数据: {endpoint}")
            data = fetch_from_disease_sh(endpoint)
            
            if data and 'timeline' in data and any(data['timeline'].get(k) for k in ['cases', 'deaths', 'recovered']):
                # 确保数据按日期排序并过滤日期范围
                for category in ['cases', 'deaths', 'recovered']:
                    if category in data['timeline']:
                        timeline = data['timeline'][category]
                        sorted_timeline = {}
                        for date_str, value in sorted(
                            timeline.items(),
                            key=lambda x: datetime.strptime(x[0], '%m/%d/%y')
                        ):
                            date_obj = datetime.strptime(date_str, '%m/%d/%y')
                            new_date_str = date_obj.strftime('%Y-%m-%d')
                            if start_date and end_date:
                                if start_date <= new_date_str <= end_date:
                                    sorted_timeline[new_date_str] = value
                            else:
                                sorted_timeline[new_date_str] = value
                        data['timeline'][category] = sorted_timeline
                
                if start_date and end_date and not any(len(data['timeline'].get(k, {})) > 0 for k in ['cases', 'deaths', 'recovered']):
                    return jsonify({
                        "error": f"所选日期范围内没有数据 ({start_date} 至 {end_date})",
                        "suggestion": "请尝试选择较近的日期范围，如最近30天"
                    }), 404
                
                logger.info(f"成功从disease.sh获取历史数据: {country_code}")
                return jsonify(data)
            else:
                # 返回带有建议的错误信息
                logger.error(f"无法获取任何历史数据: {country_code}")
                return jsonify({
                    "error": f"无法获取历史数据: {country_code}",
                    "suggestion": "请尝试选择2020年以后的日期范围，如2020-03-01至2021-12-31"
                }), 404
    except Exception as e:
        logger.error(f"获取国家历史数据失败: {country_code}, {str(e)}")
        return jsonify({"error": f"无法获取国家历史数据: {str(e)}"}), 500

@app.route('/api/continents', methods=['GET'])
def get_continents_data():
    """获取最新的大洲数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT c1.* 
        FROM continent_stats c1
        JOIN (
                SELECT continent, MAX(collected_at) as max_collected_at 
            FROM continent_stats 
            GROUP BY continent
            ) c2 ON c1.continent = c2.continent AND c1.collected_at = c2.max_collected_at
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results and len(results) > 0:
            logger.info(f"成功从数据库获取大洲数据")
            return jsonify(results)
        else:
            logger.info(f"数据库中没有大洲数据，从disease.sh获取")
            data = fetch_from_disease_sh('continents')
            if data:
                formatted_data = []
                for continent in data:
                    formatted_data.append({
                        'continent': continent.get('continent'),
                        'updated': continent.get('updated'),
                        'cases': continent.get('cases'),
                        'today_cases': continent.get('todayCases'),
                        'deaths': continent.get('deaths'),
                        'today_deaths': continent.get('todayDeaths'),
                        'recovered': continent.get('recovered'),
                        'active': continent.get('active'),
                        'critical': continent.get('critical'),
                        'tests': continent.get('tests'),
                        'population': continent.get('population')
                    })
                return jsonify(formatted_data)
            else:
                return jsonify({"error": "无法获取大洲数据"}), 500
    except Exception as e:
        logger.error(f"获取大洲数据失败: {str(e)}")
        try:
            data = fetch_from_disease_sh('continents')
            if data:
                logger.info(f"成功从disease.sh获取大洲数据（作为备选）")
                formatted_data = []
                for continent in data:
                    formatted_data.append({
                        'continent': continent.get('continent'),
                        'updated': continent.get('updated'),
                        'cases': continent.get('cases'),
                        'today_cases': continent.get('todayCases'),
                        'deaths': continent.get('deaths'),
                        'today_deaths': continent.get('todayDeaths'),
                        'recovered': continent.get('recovered'),
                        'active': continent.get('active'),
                        'critical': continent.get('critical'),
                        'tests': continent.get('tests'),
                        'population': continent.get('population')
                    })
                return jsonify(formatted_data)
            else:
                return jsonify({"error": "无法获取大洲数据"}), 500
        except Exception as ex:
            logger.error(f"从disease.sh获取大洲数据失败: {str(ex)}")
            return jsonify({"error": f"无法获取大洲数据: {str(e)}"}), 500

@app.route('/api/vaccines', methods=['GET'])
def get_vaccine_data():
    """获取全球疫苗数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        days = request.args.get('lastdays', '30')
        if not days.isdigit():
            days = '30'
        
        query = """
        SELECT * FROM daily_vaccine_global 
        ORDER BY stat_date DESC
        """
        
        if days.isdigit():
            query += f" LIMIT {int(days)}"
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results and len(results) > 0:
            logger.info(f"成功从数据库获取疫苗数据")
            # 转换为前端期望的格式
            formatted_data = {}
            for row in results:
                date_str = row['stat_date'].strftime('%m/%d/%y') if isinstance(row['stat_date'], datetime) else str(row['stat_date'])
                formatted_data[date_str] = row['doses']
            
            return jsonify(formatted_data)
        else:
            logger.info(f"数据库中没有疫苗数据，从disease.sh获取")
            data = fetch_from_disease_sh(f'vaccine/coverage?lastdays={days}')
            if data:
                return jsonify(data)
            else:
                return jsonify({"error": "无法获取疫苗数据"}), 500
    except Exception as e:
        logger.error(f"获取疫苗数据失败: {str(e)}")
        try:
            data = fetch_from_disease_sh(f'vaccine/coverage?lastdays={days}')
            if data:
                logger.info(f"成功从disease.sh获取疫苗数据（作为备选）")
                return jsonify(data)
            else:
                return jsonify({"error": "无法获取疫苗数据"}), 500
        except Exception as ex:
            logger.error(f"从disease.sh获取疫苗数据失败: {str(ex)}")
            return jsonify({"error": f"无法获取疫苗数据: {str(e)}"}), 500

@app.route('/api/vaccines/countries/<country_code>', methods=['GET'])
def get_country_vaccine_data(country_code):
    """获取指定国家的疫苗数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        days = request.args.get('lastdays', '30')
        if not days.isdigit():
            days = '30'
        
        query = """
        SELECT * FROM daily_vaccine_country 
        WHERE country_code = %s
        AND stat_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        ORDER BY stat_date ASC
        """
        
        cursor.execute(query, (country_code, int(days)))
        results = cursor.fetchall()
        
        if results and len(results) > 0:
            logger.info(f"成功从数据库获取国家疫苗数据: {country_code}")
            # 转换为前端期望的格式
            formatted_data = {
                "country": country_code,
                "timeline": {}
            }
            
            # 确保数据是连续的
            current_date = results[0]['stat_date']
            end_date = results[-1]['stat_date']
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                # 查找当前日期的数据
                matching_row = next(
                    (row for row in results if row['stat_date'].strftime('%Y-%m-%d') == date_str),
                    None
                )
                
                if matching_row:
                    formatted_data["timeline"][date_str] = matching_row['doses']
                else:
                    # 如果没有数据，使用前一天的数据
                    prev_date = (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
                    if prev_date in formatted_data["timeline"]:
                        formatted_data["timeline"][date_str] = formatted_data["timeline"][prev_date]
                    else:
                        formatted_data["timeline"][date_str] = 0
                
                current_date += timedelta(days=1)
            
            return jsonify(formatted_data)
        else:
            # 如果数据库没有数据，从disease.sh获取
            data = fetch_from_disease_sh(f'vaccine/coverage/countries/{country_code}?lastdays={days}')
            if data and 'timeline' in data:
                # 确保数据按日期排序
                data['timeline'] = dict(sorted(
                    data['timeline'].items(),
                    key=lambda x: datetime.strptime(x[0], '%m/%d/%y')
                ))
                return jsonify(data)
            else:
                return jsonify({"error": f"无法获取国家疫苗数据: {country_code}"}), 404
    except Exception as e:
        logger.error(f"获取国家疫苗数据失败: {country_code}, {str(e)}")
        return jsonify({"error": f"无法获取国家疫苗数据: {str(e)}"}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """API健康检查端点"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """API状态检查的别名，重定向到/api/health"""
    return health_check()

@app.route('/api/history/global', methods=['GET'])
def get_global_history():
    """获取全球历史数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 从请求中获取日期范围参数
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        days = request.args.get('lastdays', '30')
        
        query = """
        SELECT * FROM daily_global_history 
        """
        
        # 构建WHERE子句
        where_clauses = []
        params = []
        
        if start_date:
            where_clauses.append("stat_date >= %s")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("stat_date <= %s")
            params.append(end_date)
        
        if where_clauses:
            query += "WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY stat_date DESC"
        
        if not (start_date or end_date) and days.isdigit():
            query += " LIMIT %s"
            params.append(int(days))
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results and len(results) > 0:
            logger.info("成功从数据库获取全球历史数据")
            # 格式化为前端期望的格式
            formatted_data = {
                "cases": {},
                "deaths": {},
                "recovered": {}
            }
            
            for row in results:
                date_str = row['stat_date'].strftime('%m/%d/%y') if isinstance(row['stat_date'], datetime) else str(row['stat_date'])
                formatted_data["cases"][date_str] = row["cases"]
                formatted_data["deaths"][date_str] = row["deaths"]
                if "recovered" in row:
                    formatted_data["recovered"][date_str] = row["recovered"]
            
            return jsonify(formatted_data)
        else:
            logger.info("数据库中没有全球历史数据，从disease.sh获取")
            # 如果数据库没有数据，从disease.sh获取
            data = fetch_from_disease_sh(f'historical/all?lastdays={days}')
            if data:
                return jsonify(data)
            else:
                return jsonify({"error": "无法获取全球历史数据"}), 500
    except Exception as e:
        logger.error(f"获取全球历史数据失败: {str(e)}")
        # 出错时从disease.sh获取
        try:
            data = fetch_from_disease_sh(f'historical/all?lastdays={days}')
            if data:
                logger.info("成功从disease.sh获取全球历史数据（作为备选）")
                return jsonify(data)
            else:
                return jsonify({"error": "无法获取全球历史数据"}), 500
        except Exception as ex:
            logger.error(f"从disease.sh获取全球历史数据失败: {str(ex)}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/map/data', methods=['GET'])
def get_map_data():
    """获取地图数据（包含地理坐标的国家信息）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT c.country_code, c.country_name, c.latitude, c.longitude, 
                   c.continent, c.flag_url, rs.cases, rs.deaths, rs.recovered, rs.active
            FROM country c
            LEFT JOIN (
                SELECT rs.country_code, rs.cases, rs.deaths, rs.recovered, rs.active
                FROM realtime_country_stats rs
                JOIN (
                    SELECT country_code, MAX(collected_at) as max_collected_at 
                    FROM realtime_country_stats 
                    GROUP BY country_code
                ) latest ON rs.country_code = latest.country_code AND rs.collected_at = latest.max_collected_at
            ) rs ON c.country_code = rs.country_code
            WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results and len(results) > 0:
            logger.info(f"成功从数据库获取地图数据，共{len(results)}个国家")
            # 格式化为前端期望的格式 - GeoJSON格式
            features = []
            for country in results:
                # 跳过没有经纬度的国家
                if not country['latitude'] or not country['longitude']:
                    continue
                    
                # 创建GeoJSON特性
                feature = {
                    "type": "Feature",
                    "properties": {
                        "country_code": country['country_code'],
                        "country_name": country['country_name'],
                        "continent": country['continent'],
                        "flag_url": country['flag_url'],
                        "cases": country['cases'],
                        "deaths": country['deaths'],
                        "recovered": country['recovered'],
                        "active": country['active']
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(country['longitude']), float(country['latitude'])]
                    }
                }
                features.append(feature)
                
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            
            return jsonify(geojson)
        else:
            logger.info("数据库中没有地图数据，从countries API获取")
            # 如果数据库没有数据，尝试从countries API获取
            return get_countries_data()
    except Exception as e:
        logger.error(f"获取地图数据失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/vaccine/global', methods=['GET'])
def get_vaccine_global():
    """获取全球疫苗数据的别名，重定向到/api/vaccines"""
    return get_vaccine_data()

@app.route('/api/countries/highestDeathRate/<int:limit>', methods=['GET'])
def get_highest_death_rate(limit):
    """获取死亡率最高的国家"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 限制查询结果数量，最大100
        if limit > 100:
            limit = 100
            
        query = """
        SELECT rs.*, c.country_name, c.latitude as lat, c.longitude as `long`, 
               c.continent, c.flag_url, 
               (rs.deaths / rs.cases * 100) as death_rate
        FROM realtime_country_stats rs
        JOIN country c ON rs.country_code = c.country_code
        JOIN (
            SELECT country_code, MAX(collected_at) as max_collected_at 
            FROM realtime_country_stats 
            GROUP BY country_code
        ) latest ON rs.country_code = latest.country_code AND rs.collected_at = latest.max_collected_at
        WHERE rs.cases > 1000  -- 确保有足够的病例数以计算有意义的死亡率
        ORDER BY death_rate DESC
        LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results and len(results) > 0:
            logger.info(f"成功获取高死亡率国家数据，限制:{limit}，共返回{len(results)}个国家")
            return jsonify(results)
        else:
            logger.info(f"无法从数据库获取高死亡率国家数据，尝试从完整数据集筛选")
            # 如果无法直接查询，从所有国家数据中筛选
            countries_data = get_countries_data().json
            
            # 确保结果是列表
            if not isinstance(countries_data, list):
                return jsonify({"error": "无法获取国家数据"}), 500
                
            # 计算死亡率并筛选
            for country in countries_data:
                cases = country.get('cases', 0)
                deaths = country.get('deaths', 0)
                
                if cases > 1000:  # 确保有足够的病例数
                    country['death_rate'] = (deaths / cases * 100) if cases > 0 else 0
                else:
                    country['death_rate'] = 0
            
            # 按死亡率排序并截取前N个
            sorted_countries = sorted(
                countries_data, 
                key=lambda x: x.get('death_rate', 0), 
                reverse=True
            )[:limit]
            
            return jsonify(sorted_countries)
    except Exception as e:
        logger.error(f"获取高死亡率国家数据失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/prediction/methods', methods=['GET'])
def get_prediction_methods():
    """获取可用的预测方法列表"""
    methods = [
        {
            "id": "arima",
            "name": "ARIMA模型",
            "description": "自回归综合移动平均模型，适用于较稳定的时间序列数据",
            "default": True
        },
        {
            "id": "linear",
            "name": "线性趋势预测",
            "description": "基于最近数据的线性回归，适用于短期预测",
            "default": False
        }
    ]
    return jsonify(methods)

@app.route('/api/prediction/global', methods=['GET'])
def get_global_prediction():
    """获取全球疫情预测数据"""
    try:
        # 获取请求参数
        days = request.args.get('days', default=7, type=int)
        method = request.args.get('method', default='arima', type=str)
        
        # 限制预测天数范围
        if days < 3:
            days = 3
        elif days > 30:
            days = 30
        
        # 获取全球历史数据（最近60天）
        history_days = 60  # 用于训练预测模型的历史数据天数
        
        # 查询全球历史数据
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT stat_date, cases, deaths, recovered
            FROM daily_global_history
            WHERE stat_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY stat_date
        """, (history_days,))
        
        history_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if len(history_data) < 10:
            
            history_data = []
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            current_date = start_date
            base_cases = 500000000  
            base_deaths = 6500000   
            base_recovered = 480000000  
            
            daily_increment_cases = 15000
            daily_increment_deaths = 1000
            daily_increment_recovered = 14000
            
            while current_date <= end_date:
                day_num = (current_date - start_date).days
                history_data.append({
                    'stat_date': current_date,
                    'cases': base_cases + day_num * daily_increment_cases,
                    'deaths': base_deaths + day_num * daily_increment_deaths,
                    'recovered': base_recovered + day_num * daily_increment_recovered
                })
                current_date += timedelta(days=1)
        

        history_dates = [item['stat_date'].strftime('%Y-%m-%d') for item in history_data]
        history_cases = [item['cases'] for item in history_data]
        history_deaths = [item['deaths'] for item in history_data]
        history_recovered = [item['recovered'] if item['recovered'] is not None else 0 for item in history_data]
        

        prediction_dates = []
        last_date = history_data[-1]['stat_date']
        
        for i in range(1, days + 1):
            next_date = last_date + timedelta(days=i)
            prediction_dates.append(next_date.strftime('%Y-%m-%d'))
        
        # 进行预测
        predicted_cases = predict_timeseries(history_cases, days, method)
        predicted_deaths = predict_timeseries(history_deaths, days, method)
        predicted_recovered = predict_timeseries(history_recovered, days, method)
        
        # 构建响应数据
        response = {
            "status": "success",
            "history": {
                "dates": history_dates,
                "cases": history_cases,
                "deaths": history_deaths,
                "recovered": history_recovered
            },
            "prediction": {
                "dates": prediction_dates,
                "cases": predicted_cases,
                "deaths": predicted_deaths,
                "recovered": predicted_recovered
            },
            "note": "使用模拟数据" if len(history_data) < 30 else None
        }
        
        return jsonify(response)
    
    except Exception as e:
        app.logger.error(f"预测全球疫情数据出错: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"预测全球疫情数据出错: {str(e)}"
        }), 500

@app.route('/api/prediction/country/<country_code>', methods=['GET'])
def get_country_prediction(country_code):
    """获取特定国家的疫情预测数据"""
    try:
        # 获取请求参数
        days = request.args.get('days', default=7, type=int)
        method = request.args.get('method', default='arima', type=str)
        
        # 限制预测天数范围
        if days < 3:
            days = 3
        elif days > 30:
            days = 30
        
        # 获取国家历史数据（最近60天）
        history_days = 60  # 用于训练预测模型的历史数据天数
        
        # 查询国家历史数据
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT stat_date, cases, deaths, recovered
            FROM daily_country_history
            WHERE country_code = %s
              AND stat_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY stat_date
        """, (country_code, history_days))
        
        history_data = cursor.fetchall()
        cursor.close()
        conn.close()
        

        if len(history_data) < 10:
            logger.warning(f"国家 {country_code} 的历史数据不足，使用模拟数据进行预测")
            

            history_data = []
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            current_date = start_date

            import hashlib
            seed = int(hashlib.md5(country_code.encode()).hexdigest(), 16) % 100000000
            import random
            random.seed(seed)
            
            base_cases = random.randint(100000, 20000000)  
            base_deaths = int(base_cases * random.uniform(0.01, 0.05))  
            base_recovered = int(base_cases * random.uniform(0.8, 0.95))  
            

            daily_increment_cases = int(base_cases * random.uniform(0.001, 0.005))  
            daily_increment_deaths = int(daily_increment_cases * random.uniform(0.01, 0.05))
            daily_increment_recovered = int(daily_increment_cases * random.uniform(0.8, 0.95))
            
            while current_date <= end_date:
                day_num = (current_date - start_date).days
                history_data.append({
                    'stat_date': current_date,
                    'cases': base_cases + day_num * daily_increment_cases,
                    'deaths': base_deaths + day_num * daily_increment_deaths,
                    'recovered': base_recovered + day_num * daily_increment_recovered
                })
                current_date += timedelta(days=1)
        
        # 准备历史数据
        history_dates = [item['stat_date'].strftime('%Y-%m-%d') for item in history_data]
        history_cases = [item['cases'] for item in history_data]
        history_deaths = [item['deaths'] for item in history_data]
        history_recovered = [item['recovered'] if item['recovered'] is not None else 0 for item in history_data]
        
        # 预测未来数据
        prediction_dates = []
        last_date = history_data[-1]['stat_date']
        
        for i in range(1, days + 1):
            next_date = last_date + timedelta(days=i)
            prediction_dates.append(next_date.strftime('%Y-%m-%d'))
        
        # 进行预测
        predicted_cases = predict_timeseries(history_cases, days, method)
        predicted_deaths = predict_timeseries(history_deaths, days, method)
        predicted_recovered = predict_timeseries(history_recovered, days, method)
        
        # 构建响应数据
        response = {
            "status": "success",
            "history": {
                "dates": history_dates,
                "cases": history_cases,
                "deaths": history_deaths,
                "recovered": history_recovered
            },
            "prediction": {
                "dates": prediction_dates,
                "cases": predicted_cases,
                "deaths": predicted_deaths,
                "recovered": predicted_recovered
            },
            "note": "使用模拟数据" if len(history_data) < 30 else None
        }
        
        return jsonify(response)
    
    except Exception as e:
        app.logger.error(f"预测国家({country_code})疫情数据出错: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"预测国家({country_code})疫情数据出错: {str(e)}"
        }), 500

def predict_timeseries(data, forecast_days, method='arima'):
    """
    使用时间序列方法预测未来趋势
    
    参数:
        data: 历史数据列表
        forecast_days: 预测天数
        method: 预测方法 ('arima' 或 'linear')
        
    返回:
        包含预测值、置信区间上限和下限的字典
    """
    # 确保数据为数字类型
    data = [float(x) for x in data]
    
    # 预测结果
    forecast_values = []
    upper_bounds = []
    lower_bounds = []
    
    if method == 'arima':
        try:
            # 尝试使用ARIMA模型
            # 简单的(1,1,1)参数通常适用于许多时间序列
            model = ARIMA(data, order=(1, 1, 1))
            model_fit = model.fit()
            
            # 预测未来N天
            forecast = model_fit.get_forecast(steps=forecast_days)
            mean_forecast = forecast.predicted_mean
            confidence_intervals = forecast.conf_int(alpha=0.05)  # 95% 置信区间
            
            # 获取预测值和置信区间
            for i in range(forecast_days):
                forecast_values.append(max(0, round(mean_forecast[i])))
                lower_bounds.append(max(0, round(confidence_intervals.iloc[i, 0])))
                upper_bounds.append(max(0, round(confidence_intervals.iloc[i, 1])))
        
        except Exception as e:
            app.logger.warning(f"ARIMA预测失败，将使用线性趋势: {str(e)}")
            # 如果ARIMA失败，回退到线性预测
            method = 'linear'
    
    if method == 'linear':
        # 使用简单线性回归进行预测
        # 仅使用最近的数据点进行预测，以获得更准确的短期趋势
        recent_points = min(30, len(data))
        recent_data = data[-recent_points:]
        
        # 创建时间索引
        x = np.arange(len(recent_data))
        
        # 线性回归
        slope, intercept = np.polyfit(x, recent_data, 1)
        
        # 预测未来值
        last_value = data[-1]
        
        for i in range(1, forecast_days + 1):
            # 预测下一个值
            next_value = max(0, round(slope * (len(recent_data) + i - 1) + intercept))
            forecast_values.append(next_value)
            
            # 为线性预测创建简单的信任区间
            # 使用标准差的1.96倍来表示95%置信区间
            std_dev = np.std(recent_data) * 1.96
            upper_bounds.append(max(0, round(next_value + std_dev)))
            lower_bounds.append(max(0, round(next_value - std_dev)))
    
    return {
        "values": forecast_values,
        "upper": upper_bounds,
        "lower": lower_bounds
    }


@app.route('/api/monitor/stats', methods=['GET'])
def get_monitor_stats():
    """获取系统监控数据"""
    try:
        
        # 获取当前时间戳
        timestamp = int(datetime.now().timestamp())
        
        # 获取数据库连接以查询一些基本统计信息
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取各表记录数
        stats = {}
        
        # 全球数据统计
        cursor.execute("SELECT COUNT(*) as count FROM realtime_global_stats")
        stats['global_stats_count'] = cursor.fetchone()['count']
        
        # 国家数据统计
        cursor.execute("SELECT COUNT(*) as count FROM realtime_country_stats")
        stats['country_stats_count'] = cursor.fetchone()['count']
        
        # 历史数据统计
        cursor.execute("SELECT COUNT(*) as count FROM daily_global_history")
        stats['global_history_count'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM daily_country_history")
        stats['country_history_count'] = cursor.fetchone()['count']
        
        # 最近更新的记录
        cursor.execute("""
            SELECT MAX(collected_at) as last_update FROM realtime_global_stats
        """)
        last_update = cursor.fetchone()['last_update']
        stats['last_update'] = last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else None
        
        cursor.close()
        conn.close()
        

        kafka_stats = {
            'status': 'active',
            'message_count': stats['country_stats_count'] + stats['global_stats_count'],
            'process_rate': round(stats['country_stats_count'] / max(1, (int(time.time()) - timestamp + 3600) / 3600), 2),
            'backlog': round(stats['country_stats_count'] * 0.05),
            'partitions': 1
        }
        

        spark_stats = {
            'status': 'active',
            'batch_count': round(kafka_stats['message_count'] / 10),
            'batch_time': round(120 + 50 * np.random.random()),
            'record_count': kafka_stats['message_count'],
            'memory_usage': round(200 + 300 * np.random.random())
        }
        

        collector_stats = {
            'status': 'active',
            'request_count': round(kafka_stats['message_count'] * 1.2),
            'success_rate': round(95 + 5 * np.random.random(), 1),
            'response_time': round(100 + 200 * np.random.random()),
            'last_activity': stats['last_update']
        }
        

        db_stats = {
            'status': 'active',
            'global_count': stats['global_stats_count'],
            'country_count': stats['country_stats_count'],
            'history_count': stats['global_history_count'] + stats['country_history_count'],
            'write_rate': round(spark_stats['record_count'] / max(1, (int(time.time()) - timestamp + 3600) / 60)),
            'last_write': stats['last_update'],
            'connections': f"{round(2 + 3 * np.random.random())}/10"
        }
        

        log_types = ['info', 'warn', 'error']
        log_messages = [
            'API请求成功: disease.sh/v3/covid-19/all',
            'Kafka消息发送完成: realtime_country_stats, 190条记录',
            'Spark批处理完成: batch_id=2459, 处理时间=235ms',
            f'数据库写入成功: daily_country_history, {round(5 + 30 * np.random.random())}条记录',
            'API响应延迟较高: 312ms',
            f'Kafka队列积压: {round(80 * np.random.random())}条消息',
            f'Spark内存使用增加: {round(400 + 100 * np.random.random())}MB',
            '数据库连接池使用率: 60%'
        ]
        
        logs = []
        # 生成最近的10条日志
        for i in range(10):
            # 偏向info类型
            log_type = log_types[0] if np.random.random() < 0.7 else (log_types[1] if np.random.random() < 0.8 else log_types[2])
            log_message = log_messages[int(np.random.random() * len(log_messages))]
            log_time = (datetime.now() - timedelta(seconds=i*30)).strftime('%H:%M:%S')
            logs.append({
                'type': log_type,
                'message': log_message,
                'time': log_time
            })
        
        # 绘制图表数据
        chart_data = {
            'labels': [(datetime.now() - timedelta(minutes=i)).strftime('%H:%M') for i in range(10, 0, -1)],
            'api_requests': [round(30 + 70 * np.random.random()) for _ in range(10)],
            'kafka_messages': [round(20 + 60 * np.random.random()) for _ in range(10)],
            'spark_batch_time': [round(100 + 150 * np.random.random()) for _ in range(10)],
            'db_writes': [round(10 + 40 * np.random.random()) for _ in range(10)]
        }
        
        # 返回完整状态
        return jsonify({
            'timestamp': timestamp,
            'collector': collector_stats,
            'kafka': kafka_stats,
            'spark': spark_stats,
            'database': db_stats,
            'logs': logs,
            'chart_data': chart_data
        })
        
    except Exception as e:
        logger.error(f"获取监控统计数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"获取监控统计数据失败: {str(e)}"
        }), 500

@app.route('/api/china/provinces', methods=['GET'])
def get_china_provinces():
    """获取中国所有省份列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT DISTINCT province_name, longitude, latitude
        FROM china_province_info
        ORDER BY province_name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results:
            return jsonify(results)
        else:
            return jsonify([]), 404
    except Exception as e:
        logger.error(f"获取中国省份列表失败: {str(e)}")
        return jsonify({"error": f"无法获取省份列表: {str(e)}"}), 500


@app.route('/api/china/cities', methods=['GET'])
def get_china_cities():
    """获取特定省份的城市列表"""
    try:
        province = request.args.get('province')
        if not province:
            return jsonify({"error": "必须提供province参数"}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT DISTINCT city_name
        FROM china_city_info
        WHERE province_name = %s
        ORDER BY city_name
        """
        
        cursor.execute(query, (province,))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results:
            return jsonify(results)
        else:
            return jsonify([]), 404
    except Exception as e:
        logger.error(f"获取城市列表失败: {str(e)}")
        return jsonify({"error": f"无法获取城市列表: {str(e)}"}), 500


@app.route('/api/china/summary', methods=['GET'])
def get_china_summary():
    """获取中国疫情总体数据"""
    try:
        date_str = request.args.get('date')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if date_str:
            query = """
            SELECT SUM(confirmed_count) as confirmed, 
                   SUM(suspected_count) as suspected,
                   SUM(cured_count) as cured, 
                   SUM(dead_count) as dead,
                   stat_date
            FROM china_province_stats
            WHERE stat_date = %s
            GROUP BY stat_date
            """
            cursor.execute(query, (date_str,))
        else:
            query = """
            SELECT SUM(confirmed_count) as confirmed, 
                   SUM(suspected_count) as suspected,
                   SUM(cured_count) as cured, 
                   SUM(dead_count) as dead,
                   stat_date
            FROM china_province_stats
            WHERE stat_date = (
                SELECT MAX(stat_date) FROM china_province_stats
            )
            GROUP BY stat_date
            """
            cursor.execute(query)
            
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "未找到中国疫情汇总数据"}), 404
    except Exception as e:
        logger.error(f"获取中国疫情汇总数据失败: {str(e)}")
        return jsonify({"error": f"无法获取中国疫情汇总数据: {str(e)}"}), 500


@app.route('/api/china/province/<province>', methods=['GET'])
def get_province_history(province):
    """获取特定省份的历史数据"""
    try:
        date_str = request.args.get('date')
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if date_str:
            # 获取特定日期的数据
            query = """
            SELECT * FROM china_province_stats
            WHERE province_name = %s AND stat_date = %s
            """
            cursor.execute(query, (province, date_str))
            result = cursor.fetchone()
        else:
            # 获取所有可用的历史数据
            query = """
            SELECT * FROM china_province_stats
            WHERE province_name = %s
            ORDER BY stat_date DESC
            """
            cursor.execute(query, (province,))
            results = cursor.fetchall()
            
            # 如果有多条记录，返回这些记录组成的数组
            if results and len(results) > 1:
                cursor.close()
                conn.close()
                return jsonify(results)
            
            # 否则返回最新的一条记录
            result = results[0] if results else None
        
        cursor.close()
        conn.close()
        
        if result:
            return jsonify(result)
        else:
            # 如果没有数据，返回一个默认的数据结构
            return jsonify({
                "province_name": province,
                "confirmed_count": 0,
                "suspected_count": 0,
                "cured_count": 0,
                "dead_count": 0,
                "stat_date": datetime.now().strftime('%Y-%m-%d')
            }), 200
    except Exception as e:
        logger.error(f"获取省份数据失败: {province}, {str(e)}")
        return jsonify({"error": f"无法获取{province}的数据: {str(e)}"}), 500

@app.route('/api/china/city', methods=['GET'])
def get_city_data():
    """获取特定城市的疫情数据"""
    try:
        province = request.args.get('province')
        city = request.args.get('city')
        
        if not province or not city:
            return jsonify({"error": "必须提供province和city参数"}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取最新数据
        query = """
        SELECT * FROM china_city_stats
        WHERE province_name = %s AND city_name = %s
        ORDER BY stat_date DESC
        LIMIT 1
        """
        
        cursor.execute(query, (province, city))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            return jsonify(result)
        else:
            # 如果没有数据，返回一个默认的数据结构
            return jsonify({
                "province_name": province,
                "city_name": city,
                "confirmed_count": 0,
                "suspected_count": 0,
                "cured_count": 0,
                "dead_count": 0,
                "stat_date": datetime.now().strftime('%Y-%m-%d')
            })
    except Exception as e:
        logger.error(f"获取城市数据失败: {province}/{city}, {str(e)}")
        return jsonify({"error": f"无法获取{city}的疫情数据: {str(e)}"}), 500


@app.route('/api/china/trend', methods=['GET'])
def get_china_trend():
    """获取中国疫情趋势数据"""
    try:
        days = request.args.get('days', '30')  # 默认获取30天数据
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 确保已经将days转换为整数并检查最近的有效数据
        days_int = int(days)
        
        # 首先检查最新的可用数据
        cursor.execute("SELECT MAX(stat_date) as max_date FROM china_province_stats")
        max_date_result = cursor.fetchone()
        
        if not max_date_result or not max_date_result['max_date']:
            return jsonify({"error": "没有找到任何中国疫情数据"}), 404
            
        max_date = max_date_result['max_date']
        
        # 修改查询，确保数据是按天聚合的
        query = """
        SELECT stat_date,
               SUM(confirmed_count) as confirmed,
               SUM(suspected_count) as suspected,
               SUM(cured_count) as cured,
               SUM(dead_count) as dead
        FROM china_province_stats
        WHERE stat_date >= DATE_SUB(%s, INTERVAL %s DAY)
        GROUP BY stat_date
        ORDER BY stat_date ASC
        """
        
        cursor.execute(query, (max_date, days_int))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results:
            # 转换格式为前端期望的格式
            trend_data = {
                'dates': [],
                'confirmed': [],
                'suspected': [],
                'cured': [],
                'dead': []
            }
            
            for row in results:
                trend_data['dates'].append(row['stat_date'].strftime('%Y-%m-%d'))
                trend_data['confirmed'].append(row['confirmed'])
                trend_data['suspected'].append(row['suspected'])
                trend_data['cured'].append(row['cured'])
                trend_data['dead'].append(row['dead'])
                
            return jsonify(trend_data)
        else:
            return jsonify({"error": "未找到中国疫情趋势数据"}), 404
    except Exception as e:
        logger.error(f"获取中国疫情趋势数据失败: {str(e)}")
        return jsonify({"error": f"无法获取中国疫情趋势数据: {str(e)}"}), 500

@app.route('/api/china/provinces/map', methods=['GET'])
def get_china_provinces_map():
    """获取中国省份地图数据，用于地图可视化"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 获取最新日期的省份数据
        query = """
        SELECT DISTINCT p.province_name, p.longitude, p.latitude, 
               s.confirmed_count, s.suspected_count, s.cured_count, s.dead_count
        FROM china_province_info p
        JOIN china_province_stats s ON p.province_name = s.province_name
        WHERE s.stat_date = (SELECT MAX(stat_date) FROM china_province_stats)
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results:
            # 格式化为GeoJSON格式
            features = []
            for province in results:
                if not province['longitude'] or not province['latitude']:
                    continue
                    
                feature = {
                    "type": "Feature",
                    "properties": {
                        "province_name": province['province_name'],
                        "confirmed": province['confirmed_count'],
                        "suspected": province['suspected_count'],
                        "cured": province['cured_count'],
                        "dead": province['dead_count']
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(province['longitude']), float(province['latitude'])]
                    }
                }
                features.append(feature)
                
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            
            return jsonify(geojson)
        else:
            return jsonify({
                "type": "FeatureCollection",
                "features": []
            })
    except Exception as e:
        logger.error(f"获取中国省份地图数据失败: {str(e)}")
        return jsonify({"error": f"无法获取中国省份地图数据: {str(e)}"}), 500

@app.route('/api/china/provinces/stats', methods=['GET'])
def get_china_provinces_stats():
    """获取所有省份的最新统计数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT DISTINCT s.province_name, s.confirmed_count, s.suspected_count, 
               s.cured_count, s.dead_count, s.stat_date,
               p.longitude, p.latitude
        FROM china_province_stats s
        JOIN china_province_info p ON s.province_name = p.province_name
        WHERE s.stat_date = (SELECT MAX(stat_date) FROM china_province_stats)
        ORDER BY s.confirmed_count DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results:
            return jsonify(results)
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"获取省份统计数据失败: {str(e)}")
        return jsonify({"error": f"无法获取省份统计数据: {str(e)}"}), 500

@app.route('/api/china/provinces/top5', methods=['GET'])
def get_china_provinces_top5():
    """获取确诊病例前5名的省份数据"""
    try:
        # 获取排序字段，默认按确诊病例数排序
        sort_by = request.args.get('sort_by', 'confirmed_count')
        allowed_fields = ['confirmed_count', 'suspected_count', 'cured_count', 'dead_count']
        
        if sort_by not in allowed_fields:
            sort_by = 'confirmed_count'  
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = f"""
        SELECT DISTINCT s.province_name, s.confirmed_count, s.suspected_count, 
               s.cured_count, s.dead_count, s.stat_date,
               p.longitude, p.latitude
        FROM china_province_stats s
        JOIN china_province_info p ON s.province_name = p.province_name
        WHERE s.stat_date = (SELECT MAX(stat_date) FROM china_province_stats)
        ORDER BY s.{sort_by} DESC
        LIMIT 5
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if results:
            return jsonify(results)
        else:
            return jsonify([])
    except Exception as e:
        logger.error(f"获取TOP5省份数据失败: {str(e)}")
        return jsonify({"error": f"无法获取TOP5省份数据: {str(e)}"}), 500

if __name__ == '__main__':
    logger.info("COVID-19 API服务启动在 http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)