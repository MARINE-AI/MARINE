package controllers

import (
	"context"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
	"marine-backend/models"
)

type ReportController struct {
	DB *pgxpool.Pool
}

func NewReportController(db *pgxpool.Pool) *ReportController {
	return &ReportController{DB: db}
}

func (rc *ReportController) GetReports(c *fiber.Ctx) error {
	rows, err := rc.DB.Query(context.Background(), "SELECT id, video_id, piracy_url, match_score, detected_at FROM piracy_cases")
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).SendString("Database error")
	}
	defer rows.Close()

	var cases []models.PiracyCase
	for rows.Next() {
		var pc models.PiracyCase
		err = rows.Scan(&pc.ID, &pc.VideoID, &pc.PiracyURL, &pc.MatchScore, &pc.DetectedAt)
		if err != nil {
			return c.Status(fiber.StatusInternalServerError).SendString("Error reading record")
		}
		cases = append(cases, pc)
	}
	return c.JSON(cases)
}
