package controllers

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
)

type DashboardController struct {
	DB *pgxpool.Pool
}

func NewDashboardController(db *pgxpool.Pool) *DashboardController {
	return &DashboardController{
		DB: db,
	}
}

type UploadedVideo struct {
	ID              int         `json:"id"`
	VideoID         string      `json:"video_id"`
	VideoURL        string      `json:"video_url"`
	MatchScore      float64     `json:"match_score,omitempty"`
	UploadedPhashes interface{} `json:"uploaded_phashes"`
	AudioSpectrum   interface{} `json:"audio_spectrum,omitempty"`
	Flagged         bool        `json:"flagged"`
	UserEmail       string      `json:"user_email"`
	UploadedBy      string      `json:"uploaded_by"`
	CreatedAt       time.Time   `json:"created_at"`
	Filename        string      `json:"filename"`
	Description     string      `json:"description"`
}

func (dc *DashboardController) GetUserUploadedVideos(c *fiber.Ctx) error {
	uploaderEmail := c.Query("user_email")
	if uploaderEmail == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Missing user_email query parameter",
		})
	}

	rows, err := dc.DB.Query(context.Background(), `
		SELECT 
			id, video_id, video_url, match_score, uploaded_phashes, audio_spectrum, flagged, user_email, uploaded_by, created_at, filename, description
		FROM 
			uploaded_videos
		WHERE 
			uploaded_by = $1
	`, uploaderEmail)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "Database query error",
		})
	}
	defer rows.Close()

	var videos []UploadedVideo

	for rows.Next() {
		var video UploadedVideo
		err = rows.Scan(
			&video.ID,
			&video.VideoID,
			&video.VideoURL,
			&video.MatchScore,
			&video.UploadedPhashes,
			&video.AudioSpectrum,
			&video.Flagged,
			&video.UserEmail,
			&video.UploadedBy,
			&video.CreatedAt,
			&video.Filename,
			&video.Description,
		)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error": "Error reading record",
			})
		}
		videos = append(videos, video)
	}

	return c.JSON(videos)
}
