package controllers

import (
	"context"
	"fmt"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
	"marine-backend/models"
)

type DashboardController struct {
	DB *pgxpool.Pool
}

func NewDashboardController(db *pgxpool.Pool) *DashboardController {
	return &DashboardController{
		DB: db,
	}
}

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