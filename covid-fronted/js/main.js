// API服务器地址
const API_BASE_URL = 'http://49.232.28.106:5000/api';

// 全局变量
let worldMap = null;
let countriesData = [];
let topCountriesChart = null;

// 数字格式化函数，添加千位分隔符
function formatNumber(num) {
    return num ? num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,') : '0';
}

// 日期格式化函数
function formatDate(timestamp) {
    // 检查时间戳是否有效
    if (!timestamp || timestamp < 86400) { // 小于一天的秒数
        const now = new Date();
        return now.toLocaleString('zh-CN') + ' (当前时间)';
    }
    
    const date = new Date(timestamp * 1000); // API返回的是Unix时间戳（秒）
    return date.toLocaleString('zh-CN');
}

// 检查元素是否存在
function elementExists(id) {
    return document.getElementById(id) !== null;
}

// 安全地设置元素内容
function setElementText(id, text) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = text;
    }
}

// 初始化世界地图
function initWorldMap() {
    const mapElement = document.getElementById('world-map');
    if (!mapElement) {
        console.log('地图容器不存在，跳过地图初始化');
        return;
    }
    
    if (worldMap) {
        worldMap.remove();
    }
    
    worldMap = L.map('world-map', {
        center: [30, 10], // 调整中心点位置，更好地显示主要国家
        zoom: 2,
        minZoom: 1,
        maxZoom: 6,
        zoomControl: true,
        attributionControl: false
    });
    

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: 'abcd'
    }).addTo(worldMap);
}

// 在地图上显示国家数据
function renderCountriesOnMap(countries) {
    if (!worldMap) return;
    
    // 清除现有标记
    worldMap.eachLayer(layer => {
        if (layer instanceof L.Marker || layer instanceof L.Circle) {
            worldMap.removeLayer(layer);
        }
    });
    
    // 找出最大病例数，用于标准化圆圈大小
    const maxCases = Math.max(...countries.map(country => country.cases || 0));
    
    // 添加国家标记
    countries.forEach(country => {
        // 检查是否有地理坐标数据
        if (country.lat && country.long) {
            // 标准化圆圈大小，减小整体大小
            const normalizedSize = (country.cases || 0) / maxCases;
            const radius = Math.min(Math.max(normalizedSize * 1500000, 50000), 1000000);
            
            const color = getCircleColor(country.cases || 0);
            
            L.circle([country.lat, country.long], {
                color: color,
                fillColor: color,
                fillOpacity: 0.6,
                weight: 1,
                radius: radius
            })
            .bindPopup(`
                <div style="text-align:center"><b>${country.country_name || country.country_code}</b></div>
                <hr style="margin:5px 0">
                <table style="width:100%">
                    <tr><td>确诊:</td><td style="text-align:right;font-weight:bold">${formatNumber(country.cases)}</td></tr>
                    <tr><td>死亡:</td><td style="text-align:right;font-weight:bold">${formatNumber(country.deaths)}</td></tr>
                    <tr><td>治愈:</td><td style="text-align:right;font-weight:bold">${formatNumber(country.recovered)}</td></tr>
                </table>
            `, {
                className: 'custom-popup'
            })
            .addTo(worldMap);
        }
    });
}

// 根据确诊病例数量确定圆圈颜色
function getCircleColor(cases) {
    if (cases > 10000000) return '#d32f2f'; // 深红色
    if (cases > 5000000) return '#f44336';  // 红色
    if (cases > 1000000) return '#ff9800';  // 橙色
    if (cases > 500000) return '#ffc107';   // 琥珀色
    return '#2196f3';  // 蓝色用于低病例数
}

// 创建顶部国家排行榜
function createTopCountriesChart(countries) {
    const container = document.getElementById('top-chart-container');
    if (!container) {
        console.log('排行榜容器不存在，跳过创建排行榜');
        return;
    }
    
    // 按确诊病例数量排序
    const sortedCountries = [...countries].sort((a, b) => (b.cases || 0) - (a.cases || 0));
    const top20Countries = sortedCountries.slice(0, 20);
    
    // 准备图表数据
    const labels = top20Countries.map(c => c.country_name || c.country_code || 'Unknown');
    const casesData = top20Countries.map(c => c.cases || 0);
    
    // 清空容器
    container.innerHTML = '';
    
    // 创建图表
    const ctx = document.createElement('canvas');
    container.appendChild(ctx);
    
    if (topCountriesChart) {
        topCountriesChart.destroy();
    }
    
    topCountriesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '累计确诊人数',
                data: casesData,
                backgroundColor: [
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 159, 64, 0.8)',
                    'rgba(153, 102, 255, 0.8)',
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(255, 159, 64, 0.6)',
                    'rgba(153, 102, 255, 0.6)',
                    'rgba(255, 99, 132, 0.6)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(255, 159, 64, 0.5)',
                    'rgba(153, 102, 255, 0.5)',
                    'rgba(255, 99, 132, 0.5)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                            if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
                            return value;
                        }
                    }
                },
                y: {
                    ticks: {
                        font: {
                            size: 10 
                        }
                    }
                }
            },
            maintainAspectRatio: false,
            responsive: true
        }
    });
    
   
    container.style.height = '500px';
}

// 加载全球数据
async function loadGlobalData() {
    try {
        const response = await fetch(`${API_BASE_URL}/global`);
        const data = await response.json();
        
        console.log("全球数据:", data);
        
        // 更新全局数据显示（仅更新存在的元素）
        setElementText('update-time', formatDate(data.timestamp || 0));
        setElementText('total-cases', formatNumber(data.total_cases || 0));
        setElementText('today-cases', formatNumber(data.today_cases || 0));
        setElementText('total-deaths', formatNumber(data.total_deaths || 0));
        setElementText('today-deaths', formatNumber(data.today_deaths || 0));
        setElementText('total-recovered', formatNumber(data.total_recovered || 0));
        setElementText('today-recovered', formatNumber(data.today_recovered || 0));
        setElementText('active-cases', formatNumber(data.active_cases || 0));
        setElementText('critical-cases', formatNumber(data.critical_cases || 0));
    } catch (error) {
        console.error('加载全球数据失败:', error);
        
        console.error('无法加载全球数据，请检查网络连接或服务器状态');
        
       
        setElementText('update-time', new Date().toLocaleString('zh-CN') + ' (失败后更新)');
    }
}

// 加载国家数据
async function loadCountriesData() {
    try {
        const response = await fetch(`${API_BASE_URL}/countries`);
        const data = await response.json();
        
        console.log("国家数据:", data);
        
        // 确保数据是数组
        if (!Array.isArray(data)) {
            console.error('API返回的国家数据不是数组');
            return;
        }
        
        // 保存数据到全局变量，直接使用API返回的数据
        countriesData = data.map(country => {
            
            return {
                country_code: country.country_code || '',
                country_name: country.country_name || country.country || country.country_code || 'Unknown',
                cases: country.cases || country.total_cases || 0,
                today_cases: country.today_cases || 0,
                deaths: country.deaths || country.total_deaths || 0,
                today_deaths: country.today_deaths || 0,
                recovered: country.recovered || country.total_recovered || 0,
                active: country.active || country.active_cases || 0,
                critical: country.critical || country.critical_cases || 0,
                continent: country.continent || '',
               
                lat: country.lat || (country.country_info && country.country_info.lat) || null,
                long: country.long || (country.country_info && country.country_info.long) || null,
                flag_url: country.flag_url || (country.country_info && country.country_info.flag_url) || ''
            };
        });
        
        
        try {
            for (let i = 0; i < countriesData.length; i++) {
                if (!countriesData[i].lat || !countriesData[i].long) {
                    
                    const code = countriesData[i].country_code;
                    if (code) {
                        const detailResp = await fetch(`${API_BASE_URL}/countries/${code}`);
                        const detailData = await detailResp.json();
                        if (detailData && (detailData.lat || detailData.long)) {
                            countriesData[i].lat = detailData.lat || countriesData[i].lat;
                            countriesData[i].long = detailData.long || countriesData[i].long;
                        }
                    }
                }
            }
        } catch (detailError) {
            console.error('获取国家详情数据失败:', detailError);
        }
        
        // 按确诊病例数量排序
        countriesData.sort((a, b) => b.cases - a.cases);
        
        // 仅显示有地理坐标的国家
        const countriesWithCoords = countriesData.filter(c => c.lat && c.long);
        
        // 仅在元素存在时渲染表格
        if (elementExists('countries-data')) {
            renderCountriesTable(countriesData);
        }
        
        try {
            // 在地图上显示国家数据（如果地图已初始化）
            if (worldMap) {
                renderCountriesOnMap(countriesWithCoords);
            }
            
            // 创建顶部国家排行榜（如果容器存在）
            createTopCountriesChart(countriesData);
        } catch (vizError) {
            console.error('可视化数据时出错:', vizError);
        }
        
        // 初始化国家搜索功能（如果搜索框存在）
        initCountrySearch();
    } catch (error) {
        console.error('加载国家数据失败:', error);
        
        // 仅在表格元素存在时更新错误信息
        const tableBody = document.getElementById('countries-data');
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">加载数据失败，请稍后重试</td></tr>`;
        }
    }
}

// 渲染国家数据表格
function renderCountriesTable(data) {
    const tableBody = document.getElementById('countries-data');
    if (!tableBody) {
        console.log('国家数据表格不存在，跳过渲染表格');
        return;
    }
    
    tableBody.innerHTML = '';
    
    // 填充表格
    data.forEach(country => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                ${country.flag_url ? `<img src="${country.flag_url}" alt="${country.country_name}" width="24" class="me-2">` : ''}
                ${country.country_name || country.country_code}
            </td>
            <td>${formatNumber(country.cases)}</td>
            <td>${formatNumber(country.today_cases)}</td>
            <td>${formatNumber(country.deaths)}</td>
            <td>${formatNumber(country.recovered)}</td>
            <td>${formatNumber(country.active)}</td>
        `;
        tableBody.appendChild(row);
    });
}

// 初始化国家搜索功能
function initCountrySearch() {
    const searchInput = document.getElementById('country-search');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        // 如果countriesData已加载，直接过滤它
        if (countriesData.length > 0) {
            const filteredData = countriesData.filter(country => {
                const countryName = (country.country_name || country.country_code || '').toLowerCase();
                return countryName.includes(searchTerm);
            });
            
            renderCountriesTable(filteredData);
        } else {
            // 如果数据还未加载，则搜索DOM中的行
            const rows = document.querySelectorAll('#countries-data tr');
            rows.forEach(row => {
                const countryName = row.querySelector('td:first-child')?.textContent.toLowerCase() || '';
                if (countryName.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }
    });
}

// 添加自定义CSS样式
function addCustomStyles() {
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        .custom-popup .leaflet-popup-content-wrapper {
            border-radius: 5px;
            background-color: rgba(255, 255, 255, 0.9);
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        }
        .custom-popup .leaflet-popup-content {
            margin: 10px 12px;
            font-family: 'Microsoft YaHei', sans-serif;
        }
        .custom-popup table {
            margin-top: 5px;
        }
    `;
    document.head.appendChild(styleElement);
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    // 添加自定义样式
    addCustomStyles();
    
    // 初始化地图
    try {
        initWorldMap();
    } catch (error) {
        console.error('地图初始化失败:', error);
        // 如果地图初始化失败，也继续加载其他数据
    }
    
    // 加载数据
    loadGlobalData();
    loadCountriesData();
    
    // 每5分钟自动刷新数据
    setInterval(() => {
        loadGlobalData();
        loadCountriesData();
    }, 5 * 60 * 1000);
    
    // 处理窗口大小变化，调整地图大小
    window.addEventListener('resize', () => {
        if (worldMap) {
            try {
                worldMap.invalidateSize();
            } catch (error) {
                console.error('调整地图大小失败:', error);
            }
        }
    });
});