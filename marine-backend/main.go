package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/joho/godotenv"
	"marine-backend/config"
	"marine-backend/controllers"
	"marine-backend/eventhandlers"
	"marine-backend/services"
)

func main() {
	err := godotenv.Load()
	if err != nil {
		log.Println("No .env file found, using system environment variables")
	}

	config.DatabaseURL = os.Getenv("DATABASE_URL")
	config.KafkaBroker = os.Getenv("KAFKA_BROKER")
	config.AIServiceURL = os.Getenv("AI_SERVICE_URL")

	if config.DatabaseURL == "" || config.KafkaBroker == "" || config.AIServiceURL == "" {
		log.Fatal("Error: Please set DATABASE_URL, KAFKA_BROKER, and AI_SERVICE_URL environment variables")
	}

	db, err := pgxpool.Connect(context.Background(), config.DatabaseURL)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}
	defer db.Close()
	fmt.Println("✅ Connected to PostgreSQL")

	if err := createTables(db); err != nil {
		log.Fatalf("❌ Failed to create tables: %v", err)
	} else {
		fmt.Println("✅ Tables verified/created successfully")
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

	port := ":8080"
	fmt.Printf("🚀 Server running on http://localhost%s\n", port)
	log.Fatal(app.Listen(port))
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
		return fmt.Errorf("error creating videos table: %w", err)
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
	if err != nil {
		return fmt.Errorf("error creating piracy_cases table: %w", err)
	}

	return nil
}
