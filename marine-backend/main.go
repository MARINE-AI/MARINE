package main

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/segmentio/kafka-go"
)

// Video represents a record in the videos table.
type Video struct {
	ID          int       `json:"id"`
	Filename    string    `json:"filename"`
	Fingerprint string    `json:"fingerprint"`
	UploadedAt  time.Time `json:"uploaded_at"`
}

// PiracyCase represents a record in the piracy_cases table.
type PiracyCase struct {
	ID         int       `json:"id"`
	VideoID    int       `json:"video_id"`
	PiracyURL  string    `json:"piracy_url"`
	MatchScore float64   `json:"match_score"`
	DetectedAt time.Time `json:"detected_at"`
}

var db *pgxpool.Pool

func main() {
	var err error

	// Connect to PostgreSQL (update the connection string as needed)
	db, err = pgxpool.Connect(context.Background(), "postgres://ish:forzajuve!2@4.240.103.202:5432/marine")
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}
	defer db.Close()
	fmt.Println("Connected to PostgreSQL")

	// Create necessary tables if they don't exist
	if err = createTables(); err != nil {
		log.Fatalf("Failed to create tables: %v", err)
	}

	// Start Kafka consumer in a separate goroutine
	go startKafkaConsumer()

	// Initialize Fiber app
	app := fiber.New()

	// Route: Video Upload
	app.Post("/upload", uploadVideoHandler)

	// Route: Get Piracy Reports
	app.Get("/reports", getReportsHandler)

	// Start the Fiber server
	log.Fatal(app.Listen(":8080"))
}

// createTables creates the videos and piracy_cases tables if they do not exist.
func createTables() error {
	// Create videos table
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

	// Create piracy_cases table
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
		return err
	}
	return nil
}

// uploadVideoHandler handles the /upload endpoint.
func uploadVideoHandler(c *fiber.Ctx) error {
	// Retrieve the file from the form data
	file, err := c.FormFile("file")
	if err != nil {
		return c.Status(fiber.StatusBadRequest).SendString("No file uploaded")
	}

	// Ensure the uploads directory exists
	uploadsDir := "uploads"
	os.MkdirAll(uploadsDir, os.ModePerm)

	// Save the uploaded file
	savePath := filepath.Join(uploadsDir, file.Filename)
	if err := c.SaveFile(file, savePath); err != nil {
		return c.Status(fiber.StatusInternalServerError).SendString("Error saving file")
	}

	// Generate a simple MD5 fingerprint for the file
	fingerprint, err := generateMD5(savePath)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).SendString("Error generating fingerprint")
	}

	// Insert the video record into PostgreSQL
	var videoID int
	err = db.QueryRow(
		context.Background(),
		"INSERT INTO videos (filename, fingerprint) VALUES ($1, $2) RETURNING id",
		file.Filename, fingerprint,
	).Scan(&videoID)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).SendString("Database error")
	}

	// Optionally: Trigger Kafka event for downstream processing (e.g., AI matching)
	err = produceKafkaMessage(fmt.Sprintf("VideoUploaded:%d", videoID))
	if err != nil {
		log.Printf("Failed to produce Kafka message: %v", err)
	}

	return c.JSON(fiber.Map{
		"id":          videoID,
		"filename":    file.Filename,
		"fingerprint": fingerprint,
	})
}

// generateMD5 generates an MD5 hash for a given file.
func generateMD5(filePath string) (string, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	hasher := md5.New()
	if _, err := io.Copy(hasher, f); err != nil {
		return "", err
	}

	return hex.EncodeToString(hasher.Sum(nil)), nil
}

// produceKafkaMessage sends a message to the Kafka topic "piracy_links".
func produceKafkaMessage(message string) error {
	writer := kafka.Writer{
		Addr:         kafka.TCP("4.240.103.202:9092"),
		Topic:        "piracy_links",
		Balancer:     &kafka.LeastBytes{},
		RequiredAcks: kafka.RequireAll,
	}
	defer writer.Close()

	err := writer.WriteMessages(context.Background(),
		kafka.Message{
			Key:   []byte(strconv.FormatInt(time.Now().Unix(), 10)),
			Value: []byte(message),
		},
	)
	return err
}

// startKafkaConsumer starts a Kafka consumer that listens to the "piracy_links" topic.
func startKafkaConsumer() {
	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: []string{"4.240.103.202:9092"},
		Topic:   "piracy_links",
		GroupID: "marine-ai",
	})
	defer reader.Close()

	for {
		m, err := reader.ReadMessage(context.Background())
		if err != nil {
			log.Printf("Error reading Kafka message: %v", err)
			continue
		}
		log.Printf("Received Kafka message: %s", string(m.Value))
		// Process the message (simulate AI-based matching)
		processKafkaMessage(string(m.Value))
	}
}

// processKafkaMessage processes a Kafka message.
// For simulation, if the message starts with "PiracyFound", we record a piracy case.
func processKafkaMessage(message string) {
	// Expected format: "PiracyFound:<videoID>:<piracy_url>:<match_score>"
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
		// Insert piracy case into the database
		_, err = db.Exec(
			context.Background(),
			"INSERT INTO piracy_cases (video_id, piracy_url, match_score) VALUES ($1, $2, $3)",
			videoID, piracyURL, matchScore,
		)
		if err != nil {
			log.Printf("Failed to insert piracy case: %v", err)
		} else {
			log.Printf("Recorded piracy case for video %d", videoID)
		}
	}
}

// getReportsHandler returns all piracy cases from the database.
func getReportsHandler(c *fiber.Ctx) error {
	rows, err := db.Query(context.Background(), "SELECT id, video_id, piracy_url, match_score, detected_at FROM piracy_cases")
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).SendString("Database error")
	}
	defer rows.Close()

	var cases []PiracyCase
	for rows.Next() {
		var pc PiracyCase
		err = rows.Scan(&pc.ID, &pc.VideoID, &pc.PiracyURL, &pc.MatchScore, &pc.DetectedAt)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error reading record")
		}
		cases = append(cases, pc)
	}
	return c.JSON(cases)
}
