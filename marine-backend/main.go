package main

import (
	"context"
	"fmt"
	"log"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
	"marine-backend/config"
	"marine-backend/controllers"
	"marine-backend/eventhandlers"
	"marine-backend/services"
)

func main() {
	if config.DatabaseURL == "" || config.KafkaBroker == "" || config.AIServiceURL == "" {
		log.Fatal("Please set DATABASE_URL, KAFKA_BROKER, and AI_SERVICE_URL environment variables")
	}

	db, err := pgxpool.Connect(context.Background(), config.DatabaseURL)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}
	defer db.Close()
	fmt.Println("Connected to PostgreSQL")

	if err := createTables(db); err != nil {
		log.Fatalf("Failed to create tables: %v", err)
	}

	videoService := services.NewVideoService(db, "uploads")
	aiClient := services.NewAIServiceClient(config.AIServiceURL)

	videoController := controllers.NewVideoController(videoService, aiClient)
	reportController := controllers.NewReportController(db)

	kafkaHandler := eventhandlers.NewKafkaHandler([]string{config.KafkaBroker}, "piracy_links", "marine-ai", db)
	go kafkaHandler.Start()

	app := fiber.New()

	app.Post("/upload", videoController.Upload)
	app.Get("/reports", reportController.GetReports)

	log.Fatal(app.Listen(":8080"))
}

func createTables(db *pgxpool.Pool) error {
	createVideosTable := `
	CREATE TABLE IF NOT EXISTS videos (
		id SERIAL PRIMARY KEY,
		filename TEXT NOT NULL,
		fingerprint TEXT NOT NULL,
		uploaded_at TIMESTAMPTZ DEFAULT NOW()
	);`
	_, err := db.Exec(context.Background(), createVideosTable)
	if err != nil {
		return err
	}

	createPiracyTable := `
	CREATE TABLE IF NOT EXISTS piracy_cases (
		id SERIAL PRIMARY KEY,
		video_id INTEGER REFERENCES videos(id),
		piracy_url TEXT NOT NULL,
		match_score REAL NOT NULL,
		detected_at TIMESTAMPTZ DEFAULT NOW()
	);`
	_, err = db.Exec(context.Background(), createPiracyTable)
	return err
}
