#!/usr/bin/env python3
"""
Kafka连接测试脚本
用于验证Kafka的生产者和消费者功能是否正常
"""

import json
import time
from kafka import KafkaProducer, KafkaConsumer
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_producer():
    """测试Kafka生产者"""
    try:
        # 创建生产者
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5
        )
        logger.info("Kafka生产者连接成功")
        
        # 创建测试消息
        message = {
            'type': 'kafka_test',
            'data': {
                'test_id': int(time.time()),
                'message': 'This is a test message'
            },
            'timestamp': int(time.time())
        }
        
        # 发送消息
        future = producer.send('covid-data', message)
        record_metadata = future.get(timeout=10)
        logger.info(f"测试消息发送成功: topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")
        
        # 再发送一条不同的消息
        message2 = {
            'type': 'kafka_test',
            'data': {
                'test_id': int(time.time()),
                'message': 'This is another test message'
            },
            'timestamp': int(time.time())
        }
        future = producer.send('covid-data', message2)
        record_metadata = future.get(timeout=10)
        logger.info(f"第二条测试消息发送成功: topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")
        
        return True
    except Exception as e:
        logger.error(f"Kafka生产者测试失败: {str(e)}")
        return False

def test_consumer():
    """测试Kafka消费者"""
    try:
        # 创建消费者
        consumer = KafkaConsumer(
            'covid-data',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id=f'test-group-{int(time.time())}',  # 使用时间戳创建唯一的消费者组
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=10000  # 10秒超时
        )
        logger.info("Kafka消费者连接成功，等待消息...")
        
        # 尝试消费消息
        count = 0
        for message in consumer:
            logger.info(f"收到消息: {message.value}")
            count += 1
            if count >= 2:  # 只读取两条消息
                break
        
        if count > 0:
            logger.info(f"成功消费了 {count} 条消息")
            return True
        else:
            logger.warning("没有收到任何消息")
            return False
    except Exception as e:
        logger.error(f"Kafka消费者测试失败: {str(e)}")
        return False

def main():
    """运行Kafka测试"""
    logger.info("=== 开始Kafka连接测试 ===")
    
    # 测试生产者
    logger.info("测试Kafka生产者...")
    producer_result = test_producer()
    
    # 稍等几秒
    time.sleep(3)
    
    # 测试消费者
    logger.info("测试Kafka消费者...")
    consumer_result = test_consumer()
    
    # 输出总结
    logger.info("=== Kafka测试结果 ===")
    logger.info(f"生产者测试: {'成功' if producer_result else '失败'}")
    logger.info(f"消费者测试: {'成功' if consumer_result else '失败'}")
    
    if producer_result and consumer_result:
        logger.info("Kafka配置正常！")
    else:
        logger.warning("Kafka配置存在问题，请检查日志")

if __name__ == "__main__":
    main()