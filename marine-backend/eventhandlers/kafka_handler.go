package eventhandlers

import (
	"context"
	"log"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/segmentio/kafka-go"
)

type KafkaHandler struct {
	Reader *kafka.Reader
	DB     *pgxpool.Pool
}

func NewKafkaHandler(brokers []string, topic, groupID string, db *pgxpool.Pool) *KafkaHandler {
	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers:   brokers,
		Topic:     topic,
		GroupID:   groupID,
		MinBytes:  10e3, // 10KB
		MaxBytes:  10e6, // 10MB
	})
	return &KafkaHandler{Reader: reader, DB: db}
}

func (kh *KafkaHandler) Start() {
	defer kh.Reader.Close()
	for {
		m, err := kh.Reader.ReadMessage(context.Background())
		if err != nil {
			log.Printf("Error reading Kafka message: %v", err)
			time.Sleep(1 * time.Second)
			continue
		}
		log.Printf("Received Kafka message: %s", string(m.Value))
		kh.processMessage(string(m.Value))
	}
}

func (kh *KafkaHandler) processMessage(message string) {
	const prefix = "PiracyFound:"
	if strings.HasPrefix(message, prefix) {
		parts := strings.Split(message[len(prefix):], ":")
		if len(parts) < 3 {
			log.Println("Invalid Kafka message format")
			return
		}
		videoID, err := strconv.Atoi(parts[0])
		if err != nil {
			log.Println("Invalid video ID in Kafka message")
			return
		}
		piracyURL := parts[1]
		matchScore, err := strconv.ParseFloat(parts[2], 64)
		if err != nil {
			log.Println("Invalid match score in Kafka message")
			return
		}
		_, err = kh.DB.Exec(context.Background(),
			"INSERT INTO piracy_cases (video_id, piracy_url, match_score) VALUES ($1, $2, $3)",
			videoID, piracyURL, matchScore)
		if err != nil {
			log.Printf("Failed to insert piracy case: %v", err)
		} else {
			log.Printf("Recorded piracy case for video %d", videoID)
		}
	}
}
