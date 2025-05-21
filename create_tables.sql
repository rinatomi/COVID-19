CREATE TABLE global_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp BIGINT,
    total_cases BIGINT,
    today_cases INT,
    total_deaths BIGINT,
    today_deaths INT,
    total_recovered BIGINT,
    today_recovered INT,
    active_cases BIGINT,
    critical_cases INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE country_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp BIGINT,
    country VARCHAR(100),
    country_code VARCHAR(10),
    total_cases BIGINT,
    today_cases INT,
    total_deaths BIGINT,
    today_deaths INT,
    total_recovered BIGINT,
    active_cases BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE continent_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp BIGINT,
    continent VARCHAR(50),
    total_cases BIGINT,
    today_cases INT,
    total_deaths BIGINT,
    today_deaths INT,
    total_recovered BIGINT,
    active_cases BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vaccine_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp BIGINT,
    date DATE,
    total_vaccinations BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);