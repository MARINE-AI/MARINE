package controllers

import (
	"log"

	"github.com/gofiber/fiber/v2"
	"marine-backend/services"
)

type VideoController struct {
	VideoService    *services.VideoService
	AIServiceClient *services.AIServiceClient
}

func NewVideoController(videoService *services.VideoService, aiClient *services.AIServiceClient) *VideoController {
	return &VideoController{
		VideoService:    videoService,
		AIServiceClient: aiClient,
	}
}

func (vc *VideoController) Upload(c *fiber.Ctx) error {
	videoID, fingerprint, err := vc.VideoService.SaveVideo(c)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).SendString("Error saving video: " + err.Error())
	}

	fileHeader, err := c.FormFile("file")
	if err != nil {
		return c.Status(fiber.StatusBadRequest).SendString("Error retrieving file info: " + err.Error())
	}
	filePath := vc.VideoService.UploadsDir + "/" + fileHeader.Filename

	go func(videoID int, filePath, filename string) {
		aiResp, err := vc.AIServiceClient.ProcessVideo(filePath)
		if err != nil {
			log.Printf("Error processing video with AI: %v", err)
			return
		}
		log.Printf("AI analysis for video %d: match_score=%.2f, ai_hash=%s", videoID, aiResp.MatchScore, aiResp.ComputedHash)
		threshold := 85.0
		if aiResp.MatchScore >= threshold {
			piracyURL := "https://example.com/pirated/" + filename
			log.Printf("Recorded piracy case for video %d with score %.2f, URL: %s", videoID, aiResp.MatchScore, piracyURL)
		}
	}(videoID, filePath, fileHeader.Filename)

	return c.JSON(fiber.Map{
		"id":          videoID,
		"filename":    fileHeader.Filename,
		"fingerprint": fingerprint,
	})
}
