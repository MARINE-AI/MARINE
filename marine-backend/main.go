package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
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

	config.DatabaseURL = os.Getenv("DATABASE_URL2")
	config.KafkaBroker = os.Getenv("KAFKA_BROKER")
	config.AIServiceURL = os.Getenv("AI_SERVICE_URL")

	if config.DatabaseURL == "" || config.KafkaBroker == "" || config.AIServiceURL == "" {
		log.Fatal("Error: Please set DATABASE_URL2, KAFKA_BROKER, and AI_SERVICE_URL environment variables")
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
	dashboardController := controllers.NewDashboardController(db)
	crawlerController := controllers.NewCrawlerController()

	kafkaHandler := eventhandlers.NewKafkaHandler([]string{config.KafkaBroker}, "piracy_links", "marine-ai", db)
	go kafkaHandler.Start()

	app := fiber.New(fiber.Config{
		BodyLimit: 100 * 1024 * 1024,
	})

	app.Use(cors.New(cors.Config{
		AllowOrigins: "http://localhost:3000",
		AllowMethods: "POST, GET, OPTIONS",
		AllowHeaders: "Content-Type",
	}))

	app.Post("/upload", videoController.Upload)
	app.Get("/reports", reportController.GetReports)
	app.Get("/dashboard/videos/:user_email", dashboardController.GetUserUploadedVideos)
	app.Get("/relay-sse", dashboardController.RelaySSE)

	app.Post("/crawler/submit", crawlerController.SubmitURL)
	app.Get("/crawler/start-crawling", crawlerController.StartCrawling)

	port := ":8080"
	fmt.Printf("🚀 Server running on http://localhost%s\n", port)
	log.Fatal(app.Listen(port))
}

func createTables(db *pgxpool.Pool) error {
	createUploadedVideosTable := `
	CREATE TABLE IF NOT EXISTS uploaded_videos (
		id SERIAL PRIMARY KEY,
		video_id TEXT UNIQUE,
		video_url TEXT,
		match_score REAL,
		uploaded_phashes JSON,
		audio_spectrum JSON,
		flagged BOOLEAN DEFAULT FALSE,
		user_email TEXT,
		uploaded_by TEXT,
		created_at TIMESTAMPTZ DEFAULT NOW(),
		filename TEXT,
		description TEXT
	);`
	_, err := db.Exec(context.Background(), createUploadedVideosTable)
	if err != nil {
		return fmt.Errorf("error creating uploaded_videos table: %w", err)
	}

	createCrawledVideosTable := `
	CREATE TABLE IF NOT EXISTS crawled_videos (
		id SERIAL PRIMARY KEY,
		video_id TEXT UNIQUE,
		video_url TEXT,
		match_score REAL,
		uploaded_phashes JSON,
		audio_spectrum JSON,
		flagged BOOLEAN DEFAULT FALSE,
		created_at TIMESTAMPTZ DEFAULT NOW()
	);`
	_, err = db.Exec(context.Background(), createCrawledVideosTable)
	if err != nil {
		return fmt.Errorf("error creating crawled_videos table: %w", err)
	}

	createPiracyTable := `
	CREATE TABLE IF NOT EXISTS piracy_cases (
		id SERIAL PRIMARY KEY,
		uploaded_video_id INTEGER REFERENCES uploaded_videos(id),
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
