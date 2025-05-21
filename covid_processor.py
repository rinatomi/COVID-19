from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import mysql.connector
import time
import logging
from datetime import datetime
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/opt/covid-analysis/data-processor/processor.log'
)
logger = logging.getLogger(__name__)

# 创建Spark会话
spark = SparkSession.builder \
    .appName("CovidDataProcessor") \
    .master("local[*]") \
    .getOrCreate()

# 设置日志级别
spark.sparkContext.setLogLevel("ERROR")

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'covid_user',
    'password': 'ROOT050313cel*',
    'database': 'covid_analysis'
}

# 定义MySQL连接函数
def save_to_mysql(df, epoch_id):
    logger.info(f"开始处理批次 {epoch_id}, 数据行数: {df.count()}")
    
    try:
        # 连接MySQL
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 获取DataFrame中的数据
        rows = df.collect()
        
        processed_count = 0
        for row in rows:
            try:
                data_type = row.type
                
                # 假设row.data可能是字符串或已经是JSON对象
                if isinstance(row.data, str):
                    try:
                        data = json.loads(row.data)
                    except:
                        logger.error(f"无法解析数据: {row.data[:100]}...")
                        continue
                else:
                    data = row.data
                    
                timestamp = row.timestamp
                
                # 转换timestamp为datetime对象，用于表的collected_at字段
                collected_at = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                if data_type == "country_info":
                    # 处理国家维度数据
                    saved_count = 0
                    for country in data:
                        try:
                            country_code = country.get('country_code')
                            if not country_code:
                                logger.warning(f"跳过无国家代码的数据: {country}")
                                continue
                                
                            # 首先检查国家是否存在
                            check_query = "SELECT country_code FROM country WHERE country_code = %s"
                            cursor.execute(check_query, (country_code,))
                            exists = cursor.fetchone()
                            
                            if exists:
                                # 使用UPDATE代替REPLACE INTO以避免外键约束错误
                                query = """
                                UPDATE country 
                                SET country_name = %s, iso3 = %s, geo_id = %s, 
                                    latitude = %s, longitude = %s, continent = %s, 
                                    flag_url = %s, latest_population = %s
                                WHERE country_code = %s
                                """
                                params = (
                                    country.get('country_name'),
                                    country.get('iso3'), 
                                    country.get('geo_id'),
                                    country.get('latitude'), 
                                    country.get('longitude'),
                                    country.get('continent'), 
                                    country.get('flag_url'),
                                    country.get('latest_population'),
                                    country_code
                                )
                            else:
                                # 如果不存在，执行插入
                                query = """
                                INSERT INTO country 
                                (country_code, country_name, iso3, geo_id, latitude, longitude, 
                                 continent, flag_url, latest_population)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """
                                params = (
                                    country_code,
                                    country.get('country_name'),
                                    country.get('iso3'), 
                                    country.get('geo_id'),
                                    country.get('latitude'), 
                                    country.get('longitude'),
                                    country.get('continent'), 
                                    country.get('flag_url'),
                                    country.get('latest_population')
                                )
                                
                            cursor.execute(query, params)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"保存国家信息失败: {str(e)}, 国家: {country.get('country_name', 'unknown')}")
                    conn.commit()
                    logger.info(f"国家维度数据处理完成，成功保存 {saved_count}/{len(data)} 条记录")
                
                elif data_type == "realtime_global_stats":
                    # 处理全球实时数据
                    query = """
                    INSERT INTO realtime_global_stats 
                    (collected_at, updated, cases, today_cases, deaths, today_deaths, 
                     recovered, today_recovered, active, critical, tests, population, affected_countries)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    params = (
                        collected_at,
                        data.get('updated'),
                        data.get('cases'),
                        data.get('todayCases'),
                        data.get('deaths'),
                        data.get('todayDeaths'),
                        data.get('recovered'),
                        data.get('todayRecovered'),
                        data.get('active'),
                        data.get('critical'),
                        data.get('tests'),
                        data.get('population'),
                        data.get('affectedCountries')
                    )
                    cursor.execute(query, params)
                    conn.commit()
                    logger.info(f"全球实时数据保存成功: collected_at={collected_at}")
                
                elif data_type == "daily_global_history":
                    # 处理全球历史数据
                    saved_count = 0
                    for record in data:
                        try:
                            query = """
                            REPLACE INTO daily_global_history 
                            (stat_date, cases, deaths, recovered)
                            VALUES (%s, %s, %s, %s)
                            """
                            params = (
                                record.get('stat_date'),
                                record.get('cases'),
                                record.get('deaths'),
                                record.get('recovered')
                            )
                            cursor.execute(query, params)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"保存全球历史数据失败: {str(e)}, 日期: {record.get('stat_date', 'unknown')}")
                    conn.commit()
                    logger.info(f"全球历史数据处理完成，成功保存 {saved_count}/{len(data)} 条记录")
        
                elif data_type == "realtime_country_stats":
                    # 处理国家实时数据
                    saved_count = 0
                    for country in data:
                        try:
                            country_code = country.get('countryInfo', {}).get('iso2')
                            if not country_code:
                                continue
                                
                            query = """
                            INSERT INTO realtime_country_stats 
                            (collected_at, country_code, updated, cases, today_cases, 
                             deaths, today_deaths, recovered, today_recovered, active, 
                             critical, tests, population)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            params = (
                                collected_at,
                                country_code,
                                country.get('updated'),
                                country.get('cases'),
                                country.get('todayCases'),
                                country.get('deaths'),
                                country.get('todayDeaths'),
                                country.get('recovered'),
                                country.get('todayRecovered'),
                                country.get('active'),
                                country.get('critical'),
                                country.get('tests'),
                                country.get('population')
                            )
                            cursor.execute(query, params)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"保存国家实时数据失败: {str(e)}, 国家: {country.get('country', 'unknown')}")
                    conn.commit()
                    logger.info(f"国家实时数据处理完成，成功保存 {saved_count}/{len(data)} 条记录")
                
                elif data_type == "daily_country_history":
                    # 处理国家历史数据
                    saved_count = 0
                    for record in data:
                        try:
                            query = """
                            REPLACE INTO daily_country_history 
                            (stat_date, country_code, cases, deaths, recovered)
                            VALUES (%s, %s, %s, %s, %s)
                            """
                            params = (
                                record.get('stat_date'),
                                record.get('country_code'),
                                record.get('cases'),
                                record.get('deaths'),
                                record.get('recovered')
                            )
                            cursor.execute(query, params)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"保存国家历史数据失败: {str(e)}, 国家: {record.get('country_code', 'unknown')}, 日期: {record.get('stat_date', 'unknown')}")
                    conn.commit()
                    logger.info(f"国家历史数据处理完成，成功保存 {saved_count}/{len(data)} 条记录")
                
                elif data_type == "continent_stats":
                    # 处理大洲数据
                    saved_count = 0
                    for continent in data:
                        try:
                            query = """
                            INSERT INTO continent_stats 
                            (collected_at, continent, updated, cases, today_cases, 
                             deaths, today_deaths, recovered, active, critical, 
                             tests, population)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            params = (
                                collected_at,
                                continent.get('continent'),
                                continent.get('updated'),
                                continent.get('cases'),
                                continent.get('todayCases'),
                                continent.get('deaths'),
                                continent.get('todayDeaths'),
                                continent.get('recovered'),
                                continent.get('active'),
                                continent.get('critical'),
                                continent.get('tests'),
                                continent.get('population')
                            )
                            cursor.execute(query, params)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"保存大洲数据失败: {str(e)}, 大洲: {continent.get('continent', 'unknown')}")
                    conn.commit()
                    logger.info(f"大洲数据处理完成，成功保存 {saved_count}/{len(data)} 条记录")
                
                elif data_type == "daily_vaccine_global":
                    # 处理全球疫苗数据
                    saved_count = 0
                    for record in data:
                        try:
                            query = """
                            REPLACE INTO daily_vaccine_global 
                            (stat_date, doses)
                            VALUES (%s, %s)
                            """
                            params = (
                                record.get('stat_date'),
                                record.get('doses')
                            )
                            cursor.execute(query, params)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"保存全球疫苗数据失败: {str(e)}, 日期: {record.get('stat_date', 'unknown')}")
                    conn.commit()
                    logger.info(f"全球疫苗数据处理完成，成功保存 {saved_count}/{len(data)} 条记录")
                
                elif data_type == "daily_vaccine_country":
                    # 处理国家疫苗数据
                    saved_count = 0
                    for record in data:
                        try:
                            query = """
                            REPLACE INTO daily_vaccine_country 
                            (stat_date, country_code, doses)
                            VALUES (%s, %s, %s)
                            """
                            params = (
                                record.get('stat_date'),
                                record.get('country_code'),
                                record.get('doses')
                            )
                            cursor.execute(query, params)
                            saved_count += 1
                        except Exception as e:
                            logger.error(f"保存国家疫苗数据失败: {str(e)}, 国家: {record.get('country_code', 'unknown')}, 日期: {record.get('stat_date', 'unknown')}")
                    conn.commit()
                    logger.info(f"国家疫苗数据处理完成，成功保存 {saved_count}/{len(data)} 条记录")
                
                processed_count += 1
            except Exception as e:
                logger.error(f"处理数据失败: {str(e)}, 数据类型: {row.type if hasattr(row, 'type') else 'unknown'}")
        
        # 关闭连接
        cursor.close()
        conn.close()
        logger.info(f"批次 {epoch_id} 处理完成, 成功处理 {processed_count}/{len(rows)} 条数据")
    
    except Exception as e:
        logger.error(f"批次 {epoch_id} 处理失败: {str(e)}")
        # 确保连接被关闭
        try:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()
        except Exception:
            pass

# 主程序
def main():
    logger.info("开始从Kafka读取数据流...")

    try:
        # 从Kafka读取数据，增加更多配置选项
        df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "covid-data") \
            .option("startingOffsets", "earliest") \
            .option("failOnDataLoss", "false") \
            .option("kafka.group.id", "covid_processor_new_group") \
            .option("maxOffsetsPerTrigger", "1000") \
            .load()

        # 添加更多调试信息
        logger.info("Kafka连接配置完成，尝试读取数据...")

        # 解析Kafka消息，允许data字段接收复杂类型
        schema = StructType([
            StructField("type", StringType()),
            StructField("data", StringType()),  # 保持为StringType但后续用另一种方式处理
            StructField("timestamp", LongType())
        ])

        # 先解析为字符串再转换为正确格式
        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data")
        ).select("data.*")

        # 添加调试输出
        logger.info("读取Kafka数据成功，设置处理器...")
        logger.info(f"Schema: {parsed_df.schema}")

        # 将处理后的数据写入MySQL
        query = parsed_df.writeStream \
            .foreachBatch(save_to_mysql) \
            .outputMode("append") \
            .trigger(processingTime="10 seconds") \
            .start()

        logger.info("流处理作业已启动...")
        # 等待终止
        query.awaitTermination()

    except Exception as e:
        logger.error(f"启动流处理失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()