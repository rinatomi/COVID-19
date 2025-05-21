import requests
import json
import time
from kafka import KafkaProducer
import logging
import traceback
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='/opt/covid-analysis/data-collector/collector.log')
logger = logging.getLogger(__name__)

# 添加控制台处理器以便于调试
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)

# Kafka配置
try:
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=5  # 增加重试次数
    )
    logger.info("Kafka连接成功")
except Exception as e:
    logger.error(f"Kafka连接失败: {str(e)}")
    raise

# Disease.sh API URLs
GLOBAL_DATA_URL = "https://disease.sh/v3/covid-19/all"
COUNTRIES_DATA_URL = "https://disease.sh/v3/covid-19/countries"
HISTORICAL_DATA_URL = "https://disease.sh/v3/covid-19/historical/all"
CONTINENTS_DATA_URL = "https://disease.sh/v3/covid-19/continents"
VACCINE_GLOBAL_URL = "https://disease.sh/v3/covid-19/vaccine/coverage"
VACCINE_COUNTRY_URL = "https://disease.sh/v3/covid-19/vaccine/coverage/countries"
COUNTRY_HISTORY_URL = "https://disease.sh/v3/covid-19/historical"

def fetch_api_data(url, params=None, retry_count=3, retry_delay=5):
    """通用API数据获取函数，支持重试"""
    for attempt in range(retry_count):
        try:
            logger.info(f"尝试请求API: {url}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()  # 抛出HTTP错误
            data = response.json()
            logger.info(f"成功获取API数据: {url}")
            return data
        except requests.exceptions.RequestException as e:
            logger.warning(f"API请求失败 (尝试 {attempt+1}/{retry_count}): {url} - {str(e)}")
            if attempt < retry_count - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"API请求最终失败: {url} - {str(e)}")
                raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {url} - {str(e)}")
            raise

def send_to_kafka(topic, data_type, data):
    """发送数据到Kafka，支持重试和错误处理"""
    if not data:
        logger.warning(f"没有数据可发送到Kafka: {data_type}")
        return
        
    message = {
        'type': data_type,
        'data': data,
        'timestamp': int(time.time())
    }
    
    # 添加日志记录消息内容
    logger.info(f"准备发送数据到Kafka: {data_type}, 消息大小: {len(json.dumps(message))} bytes")
    
    try:
        future = producer.send('covid-data', message)
        # 等待确认消息已发送
        record_metadata = future.get(timeout=10)
        logger.info(f"数据成功发送到Kafka: {data_type}, 数据量: {len(data) if isinstance(data, list) else 1}")
        logger.info(f"发送详情: topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")
    except Exception as e:
        logger.error(f"发送数据到Kafka失败: {data_type} - {str(e)}")
        logger.error(traceback.format_exc())

def initialize_country_data():
    """初始化国家基础信息并存入country表"""
    try:
        countries_data = fetch_api_data(COUNTRIES_DATA_URL)
        if not countries_data:
            logger.error("获取国家数据失败，返回为空")
            return
            
        country_list = []
        
        for country in countries_data:
            if not country.get('countryInfo', {}).get('iso2'):
                logger.warning(f"跳过没有国家代码的国家: {country.get('country', 'unknown')}")
                continue
                
            country_info = {
                'country_code': country.get('countryInfo', {}).get('iso2'),
                'country_name': country.get('country'),
                'iso3': country.get('countryInfo', {}).get('iso3'),
                'geo_id': country.get('countryInfo', {}).get('_id'),
                'latitude': country.get('countryInfo', {}).get('lat'),
                'longitude': country.get('countryInfo', {}).get('long'),
                'continent': country.get('continent'),
                'flag_url': country.get('countryInfo', {}).get('flag'),
                'latest_population': country.get('population')
            }
            
            # 验证地理坐标存在
            if country_info['latitude'] is None or country_info['longitude'] is None:
                logger.warning(f"国家缺少地理坐标: {country_info['country_name']} (code: {country_info['country_code']})")
            
            country_list.append(country_info)
        
        # 日志记录坐标情况
        countries_with_coords = [c for c in country_list if c['latitude'] is not None and c['longitude'] is not None]
        logger.info(f"收集了{len(countries_with_coords)}/{len(country_list)}个国家的地理坐标")
        
        # 发送到Kafka
        send_to_kafka('covid-data', 'country_info', country_list)
        logger.info(f"国家基础信息已收集并发送到Kafka，共{len(country_list)}个国家")
    except Exception as e:
        logger.error(f"初始化国家数据失败: {str(e)}")
        logger.error(traceback.format_exc())

def collect_global_history():
    """收集全球历史数据"""
    try:
        response = fetch_api_data(f"{HISTORICAL_DATA_URL}?lastdays=all")
        
        # 将数据重组为按日期的记录
        daily_records = []
        cases_data = response.get('cases', {})
        deaths_data = response.get('deaths', {})
        recovered_data = response.get('recovered', {})
        
        for date in cases_data:
            daily_records.append({
                'stat_date': date,
                'cases': cases_data.get(date, 0),
                'deaths': deaths_data.get(date, 0),
                'recovered': recovered_data.get(date, 0)
            })
        
        send_to_kafka('covid-data', 'daily_global_history', daily_records)
        logger.info(f"全球历史数据已收集并发送到Kafka，共{len(daily_records)}条记录")
    except Exception as e:
        logger.error(f"收集全球历史数据失败: {str(e)}")
        logger.error(traceback.format_exc())

def collect_country_history():
    """收集国家历史数据"""
    try:
        # 首先获取所有国家列表
        countries_data = fetch_api_data(COUNTRIES_DATA_URL)
        
        # 确保国家数据有效
        if not countries_data or not isinstance(countries_data, list):
            logger.error(f"获取国家列表失败，返回数据类型: {type(countries_data)}")
            return
            
        # 选择有效的国家（有ISO2代码的）
        valid_countries = []
        for country in countries_data:
            iso2 = country.get('countryInfo', {}).get('iso2')
            if iso2:
                valid_countries.append(iso2)
            else:
                logger.warning(f"跳过没有ISO2代码的国家: {country.get('country', 'unknown')}")
        
   
        selected_countries = valid_countries[:30]
        
        all_country_history = []
        
        for country_code in selected_countries:
            try:
                response = fetch_api_data(f"{COUNTRY_HISTORY_URL}/{country_code}?lastdays=all")
                
                # 检查响应格式
                if 'timeline' in response:
                    timeline = response['timeline']
                    cases = timeline.get('cases', {})
                    deaths = timeline.get('deaths', {})
                    recovered = timeline.get('recovered', {})
                    
                    for date in cases:
                        all_country_history.append({
                            'country_code': country_code,
                            'stat_date': date,
                            'cases': cases.get(date, 0),
                            'deaths': deaths.get(date, 0),
                            'recovered': recovered.get(date, 0) if recovered else 0
                        })
                else:
                    logger.warning(f"国家历史数据格式不符合预期: {country_code}, 数据: {response}")
                
                # 添加延迟避免API限制
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"收集国家历史数据失败，国家代码: {country_code}, 错误: {str(e)}")
        
        send_to_kafka('covid-data', 'daily_country_history', all_country_history)
        logger.info(f"国家历史数据已收集并发送到Kafka，共{len(all_country_history)}条记录")
    except Exception as e:
        logger.error(f"收集国家历史数据总体失败: {str(e)}")
        logger.error(traceback.format_exc())

def collect_vaccine_data():
    """收集全球和国家疫苗数据"""
    try:
        # 全球疫苗数据
        global_vaccine_data = fetch_api_data(f"{VACCINE_GLOBAL_URL}?lastdays=all")
        
        # 转换为列表格式
        global_vaccine_records = []
        for date, doses in global_vaccine_data.items():
            global_vaccine_records.append({
                'stat_date': date,
                'doses': doses
            })
        
        send_to_kafka('covid-data', 'daily_vaccine_global', global_vaccine_records)
        logger.info(f"全球疫苗数据已收集并发送到Kafka，共{len(global_vaccine_records)}条记录")
        
        # 国家疫苗数据
        countries_vaccine_data = fetch_api_data(f"{VACCINE_COUNTRY_URL}?lastdays=all")
        
        country_vaccine_records = []
        for country_data in countries_vaccine_data:
            country_code = country_data.get('country')
            timeline = country_data.get('timeline', {})
            
            for date, doses in timeline.items():
                country_vaccine_records.append({
                    'country_code': country_code,
                    'stat_date': date,
                    'doses': doses
                })
        
        send_to_kafka('covid-data', 'daily_vaccine_country', country_vaccine_records)
        logger.info(f"国家疫苗数据已收集并发送到Kafka，共{len(country_vaccine_records)}条记录")
    except Exception as e:
        logger.error(f"收集疫苗数据失败: {str(e)}")
        logger.error(traceback.format_exc())

def collect_realtime_data():
    """收集实时数据（全球、国家和大洲）"""
    try:
        # 全球实时数据
        global_data = fetch_api_data(GLOBAL_DATA_URL)
        timestamp = int(time.time())
        
        # 确保有返回结果
        if not global_data:
            logger.error("获取全球实时数据失败，返回为空")
            return
            
        # 添加时间戳
        global_data['timestamp'] = timestamp
        
        send_to_kafka('covid-data', 'realtime_global_stats', global_data)
        logger.info("全球实时数据已收集并发送到Kafka")
        
        # 国家实时数据
        countries_data = fetch_api_data(COUNTRIES_DATA_URL)
        
        # 确保有返回结果
        if not countries_data or not isinstance(countries_data, list):
            logger.error(f"获取国家实时数据失败，返回数据类型: {type(countries_data)}")
            return
            
        # 添加时间戳
        countries_formatted = []
        for country in countries_data:
            # 验证坐标数据
            lat = country.get('countryInfo', {}).get('lat')
            long = country.get('countryInfo', {}).get('long')
            
            # 输出缺少坐标的国家
            if lat is None or long is None:
                logger.warning(f"国家实时数据缺少地理坐标: {country.get('country', 'unknown')}")
            
            country['timestamp'] = timestamp
            countries_formatted.append(country)
        
        send_to_kafka('covid-data', 'realtime_country_stats', countries_formatted)
        logger.info(f"国家实时数据已收集并发送到Kafka，共{len(countries_formatted)}个国家")
        
        # 大洲实时数据
        continents_data = fetch_api_data(CONTINENTS_DATA_URL)
        
        # 确保有返回结果
        if not continents_data or not isinstance(continents_data, list):
            logger.error(f"获取大洲实时数据失败，返回数据类型: {type(continents_data)}")
            return
            
        continents_formatted = []
        for continent in continents_data:
            continent['timestamp'] = timestamp
            continents_formatted.append(continent)
        
        send_to_kafka('covid-data', 'continent_stats', continents_formatted)
        logger.info(f"大洲实时数据已收集并发送到Kafka，共{len(continents_formatted)}个大洲")
    except Exception as e:
        logger.error(f"收集实时数据失败: {str(e)}")
        logger.error(traceback.format_exc())

def collect_data():
    """收集所有类型的数据"""
    start_time = time.time()
    logger.info("开始收集所有类型数据")
    
    try:
        # 收集实时数据
        collect_realtime_data()
        
        # 每天只需收集一次的数据
        current_hour = time.localtime().tm_hour
        if current_hour == 0:  # 每天0点收集
            logger.info("执行每日数据采集任务")
            initialize_country_data()
            collect_global_history()
            collect_country_history()
            collect_vaccine_data()
            
        end_time = time.time()
        logger.info(f"所有数据收集完成，耗时: {end_time - start_time:.2f}秒")
    except Exception as e:
        logger.error(f"数据收集主函数失败: {str(e)}")
        logger.error(traceback.format_exc())

def run_collector(interval=3600):
    """定时运行数据收集器
    
    Args:
        interval: 收集数据的时间间隔（秒），默认为1小时
    """
    logger.info(f"COVID-19数据收集器启动，收集间隔: {interval}秒")
    
    # 首次运行时初始化国家数据
    initialize_country_data()
    
    while True:
        try:
            collect_data()
            logger.info(f"等待{interval}秒后进行下一次数据收集")
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("收到中断信号，数据收集器停止")
            break
        except Exception as e:
            logger.error(f"数据收集器遇到错误: {str(e)}")
            logger.error(traceback.format_exc())
            # 出错后等待一段时间再重试
            time.sleep(60)

def send_test_data():
    """发送测试数据到Kafka，验证Kafka连接是否正常"""
    logger.info("发送测试数据到Kafka...")
    
    test_data = {
        "test_key": "test_value",
        "timestamp": int(time.time())
    }
    
    send_to_kafka('covid-data', 'test_data', test_data)
    logger.info("测试数据发送完成")

if __name__ == "__main__":
    logger.info("COVID-19数据收集器已启动")
    
    # 首先发送测试数据确认Kafka连接正常
    send_test_data()
    
    # 强制立即收集一次实时数据
    collect_realtime_data()
    
    # 启动定时收集器
    run_collector()