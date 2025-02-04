import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
from app.config import settings
from loguru import logger

producer: AIOKafkaProducer = None

async def ensure_topic(topic: str, num_partitions: int = 3, replication_factor: int = 1):
    admin_client = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    await admin_client.start()
    try:
        topics = await admin_client.list_topics()
        if topic not in topics:
            new_topic = NewTopic(name=topic, num_partitions=num_partitions, replication_factor=replication_factor)
            try:
                await admin_client.create_topics([new_topic])
                logger.info(f"Created topic: {topic}")
            except TopicAlreadyExistsError:
                logger.info(f"Topic {topic} already exists.")
    except Exception as e:
        logger.error(f"Error ensuring topic '{topic}': {e}")
    finally:
        await admin_client.close()

async def get_kafka_producer() -> AIOKafkaProducer:
    global producer
    await ensure_topic(settings.kafka_video_download_topic)
    await ensure_topic(settings.kafka_video_chunks_topic)
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id="video_crawler_producer",
            compression_type="gzip",
            max_request_size=10000000  # 10 MB, adjust as needed.
        )
        await producer.start()
        logger.info("Kafka producer started")
    return producer

async def close_kafka_producer():
    global producer
    if producer:
        await producer.stop()
        logger.info("Kafka producer stopped")

async def get_kafka_consumer(topic: str, group_id: str) -> AIOKafkaConsumer:
    await ensure_topic(topic)
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="earliest"
    )
    await consumer.start()
    logger.info(f"Kafka consumer started for topic '{topic}'")
    return consumer
