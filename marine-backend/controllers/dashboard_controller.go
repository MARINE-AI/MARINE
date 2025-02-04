package controllers

import (
	"context"
	"fmt"
	"net/http"
	"net/url"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
	"marine-backend/models"
)

// DashboardController handles dashboard-related endpoints.
type DashboardController struct {
	DB *pgxpool.Pool
}

// NewDashboardController creates a new DashboardController.
func NewDashboardController(db *pgxpool.Pool) *DashboardController {
	return &DashboardController{
		DB: db,
	}
}

// GetUserUploadedVideos retrieves all videos uploaded by the given user.
func (dc *DashboardController) GetUserUploadedVideos(c *fiber.Ctx) error {
	encodedEmail := c.Params("user_email")
	if encodedEmail == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Missing user_email route parameter",
		})
	}

	rows, err := dc.DB.Query(context.Background(), `
		SELECT 
			id, user_email, filename, title, description, fingerprint, 
			hash_vector, audio_spectrum, created_at
		FROM 
			videos
		WHERE 
			user_email = $1
	`, encodedEmail)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": fmt.Sprintf("Database query error: %v", err),
		})
	}
	defer rows.Close()

	var videos []models.Video

	for rows.Next() {
		var video models.Video
		err = rows.Scan(
			&video.ID,
			&video.UserEmail,
			&video.Filename,
			&video.Title,
			&video.Description,
			&video.Fingerprint,
			&video.HashVector,
			&video.AudioSpectrum,
			&video.CreatedAt,
		)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": fmt.Sprintf("Error reading record: %v", err),
			})
		}
		videos = append(videos, video)
	}

	return c.JSON(videos)
}

// RelaySSE connects to the FastAPI SSE endpoint and relays events to the client.
func (dc *DashboardController) RelaySSE(c *fiber.Ctx) error {
	userEmail := c.Query("user_email")
	if userEmail == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Missing user_email query parameter",
		})
	}

	// Define the FastAPI SSE endpoint URL.
	fastapiSSEURL := "http://localhost:8000/sse"

	// Parse the URL and add the user_email query parameter.
	u, err := url.Parse(fastapiSSEURL)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": fmt.Sprintf("Error parsing FastAPI SSE URL: %v", err),
		})
	}
	q := u.Query()
	q.Set("user_email", userEmail)
	u.RawQuery = q.Encode()

	// Create a GET request (note: GET, not POST) to the FastAPI SSE endpoint.
	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": fmt.Sprintf("Error creating request: %v", err),
		})
	}

	// Perform the request.
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": fmt.Sprintf("Error connecting to SSE endpoint: %v", err),
		})
	}

	// Set appropriate SSE headers and stream the response body.
	c.Set("Content-Type", "text/event-stream")
	c.Set("Cache-Control", "no-cache")
	c.Set("Connection", "keep-alive")

	return c.SendStream(resp.Body)
}
