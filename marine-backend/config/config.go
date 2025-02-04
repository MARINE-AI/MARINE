package config

import "os"

var (
    DatabaseURL  = os.Getenv("DATABASE_URL2")
    KafkaBroker  = os.Getenv("KAFKA_BROKER")
    AIServiceURL = os.Getenv("AI_SERVICE_URL")
)
