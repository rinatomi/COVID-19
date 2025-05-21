#!/usr/bin/env python3
"""
更新国家地理坐标数据脚本

这个脚本从disease.sh API获取国家地理坐标并更新MySQL数据库中的country表
"""

import requests
import mysql.connector
import logging
import time
import sys
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/covid-analysis/update_coordinates.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'covid_user',
    'password': 'ROOT050313cel*',
    'database': 'covid_analysis'
}

# Disease.sh API URL
COUNTRIES_DATA_URL = "https://disease.sh/v3/covid-19/countries"

def fetch_api_data(url):
    """从API获取数据"""
    try:
        logger.info(f"请求API: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"成功获取API数据，共{len(data)}条记录")
        return data
    except Exception as e:
        logger.error(f"API请求失败: {url} - {str(e)}")
        raise

def get_countries_without_coordinates():
    """获取数据库中缺少地理坐标的国家"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT country_code, country_name
        FROM country
        WHERE latitude IS NULL OR longitude IS NULL
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        logger.info(f"数据库中有{len(results)}个国家缺少地理坐标")
        return results
    except Exception as e:
        logger.error(f"查询缺少坐标的国家失败: {str(e)}")
        raise

def get_all_countries():
    """获取数据库中所有国家"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT country_code, country_name, latitude, longitude
        FROM country
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        countries_with_coords = [c for c in results if c['latitude'] is not None and c['longitude'] is not None]
        logger.info(f"数据库中共有{len(results)}个国家，其中{len(countries_with_coords)}个有地理坐标")
        return results
    except Exception as e:
        logger.error(f"查询所有国家失败: {str(e)}")
        raise

def update_country_coordinates(country_code, latitude, longitude):
    """更新国家的地理坐标"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        query = """
        UPDATE country
        SET latitude = %s, longitude = %s
        WHERE country_code = %s
        """
        
        cursor.execute(query, (latitude, longitude, country_code))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info(f"成功更新国家坐标: {country_code}, 纬度: {latitude}, 经度: {longitude}")
        return True
    except Exception as e:
        logger.error(f"更新国家坐标失败: {country_code} - {str(e)}")
        return False

def main():
    """主函数"""
    try:
        logger.info("开始更新国家地理坐标")
        
        # 获取数据库中的所有国家
        db_countries = get_all_countries()
        db_countries_map = {c['country_code']: c for c in db_countries}
        
        # 获取API中的国家数据
        api_countries = fetch_api_data(COUNTRIES_DATA_URL)
        
        # 记录更新统计信息
        updated_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 遍历API数据并更新数据库
        for country in api_countries:
            country_code = country.get('countryInfo', {}).get('iso2')
            if not country_code:
                skipped_count += 1
                continue
                
            # 从API获取坐标
            lat = country.get('countryInfo', {}).get('lat')
            long = country.get('countryInfo', {}).get('long')
            
            # 如果API中有坐标，而数据库中没有或坐标为NULL
            if lat is not None and long is not None:
                db_country = db_countries_map.get(country_code)
                if db_country:
                    # 检查数据库中是否缺少坐标
                    if db_country['latitude'] is None or db_country['longitude'] is None:
                        # 更新坐标
                        if update_country_coordinates(country_code, lat, long):
                            updated_count += 1
                        else:
                            failed_count += 1
                    else:
                        skipped_count += 1
                else:
                    logger.warning(f"数据库中找不到国家: {country_code} ({country.get('country')})")
            else:
                logger.warning(f"API中国家缺少坐标: {country_code} ({country.get('country')})")
        
        logger.info(f"坐标更新完成: 更新 {updated_count} 个, 跳过 {skipped_count} 个, 失败 {failed_count} 个")
        
        # 检查是否还有国家缺少坐标
        countries_without_coords = get_countries_without_coordinates()
        if countries_without_coords:
            logger.warning(f"仍有 {len(countries_without_coords)} 个国家缺少坐标:")
            for country in countries_without_coords:
                logger.warning(f"  - {country['country_code']}: {country['country_name']}")
        else:
            logger.info("所有国家都已有坐标")
            
        return True
    except Exception as e:
        logger.error(f"更新坐标主函数失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 