import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
import os

# ✅ 1. 数据库连接
db_url = 'mysql+pymysql://root:root@localhost:3306/covid_data'
engine = create_engine(db_url)

# ✅ 2. 设置月份（用于筛选）
target_month = '2022.12'

# ✅ 3. 获取 GitHub releases 页中所有包含 target_month 的版本
def get_versions_by_month(month: str, max_pages=64):#查找页数控制，2022年12月数据大概在61-64页中间
    versions = set()
    headers = {"User-Agent": "Mozilla/5.0"}

    for page in range(61, max_pages + 1):
        url = f"https://github.com/BlankerL/DXY-COVID-19-Data/releases?page={page}"
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', class_='Link--primary')
        print(f"📄 第 {page} 页抓到 {len(links)} 个版本候选：")
        for link in links:
            version = link.text.strip()
            print("🔍 版本候选 =", version)
            if version.startswith(month):
                versions.add(version)

    return sorted(versions)

# ✅ 4. 处理每个版本的 DXYArea.csv
def import_dxyarea(version: str):
    url = f"https://github.com/BlankerL/DXY-COVID-19-Data/releases/download/{version}/DXYArea.csv"
    print(f"\n📥 正在导入版本：{version}")
    try:
        df = pd.read_csv(url, encoding='utf-8')
        df = df[df['countryName'] == '中国'].copy()
        df.fillna('', inplace=True)
        df['updateTime'] = pd.to_datetime(df['updateTime'])

        # location_info
        df_location = df[[
            'provinceName', 'provinceEnglishName', 'province_zipCode',
            'cityName', 'cityEnglishName', 'city_zipCode',
            'countryName', 'countryEnglishName'
        ]].drop_duplicates()
        df_location.columns = [
            'province_name', 'province_english_name', 'province_zip_code',
            'city_name', 'city_english_name', 'city_zip_code',
            'country_name', 'country_english_name'
        ]
        df_location.to_sql('location_info', con=engine, if_exists='replace', index=False)

        # province_stat
        df_province = df[[
            'provinceName', 'province_confirmedCount', 'province_suspectedCount',
            'province_curedCount', 'province_deadCount', 'updateTime'
        ]].drop_duplicates(subset='provinceName')
        df_province.columns = [
            'province_name', 'confirmed_count', 'suspected_count',
            'cured_count', 'dead_count', 'update_time'
        ]
        df_province.to_sql('province_stat', con=engine, if_exists='replace', index=False)

        # city_stat
        df_city = df[[
            'provinceName', 'cityName', 'city_confirmedCount', 'city_suspectedCount',
            'city_curedCount', 'city_deadCount', 'updateTime'
        ]]
        df_city = df_city[df_city['cityName'] != '']
        df_city.columns = [
            'province_name', 'city_name', 'confirmed_count',
            'suspected_count', 'cured_count', 'dead_count', 'update_time'
        ]
        df_city.to_sql('city_stat', con=engine, if_exists='replace', index=False)

        print(f"✅ 导入完成：{version}")
    except Exception as e:
        print(f"❌ 导入失败 {version}: {e}")

# ✅ 5. 主执行
if __name__ == '__main__':
    versions = get_versions_by_month(target_month)
    if not versions:
        print(f"❗ 未找到 {target_month} 的版本")
    else:
        print(f"📌 共找到 {len(versions)} 个版本：{versions}")
        for v in versions:
            import_dxyarea(v)
