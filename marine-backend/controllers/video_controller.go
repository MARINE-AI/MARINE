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
	log.Println("[Upload] Received upload request")

	fileHeader, err := c.FormFile("file")
	if err != nil {
		log.Printf("[Upload] ❌ Error retrieving file info: %v", err)
		return c.Status(fiber.StatusBadRequest).SendString("Error retrieving file info: " + err.Error())
	}
	log.Printf("[Upload] ✅ File received: %+v", fileHeader)

	filePath := vc.VideoService.UploadsDir + "/" + fileHeader.Filename
	log.Printf("[Upload] 📂 File will be saved to: %s", filePath)

	if err := c.SaveFile(fileHeader, filePath); err != nil {
		log.Printf("[Upload] ❌ Error saving file to disk: %v", err)
		return c.Status(fiber.StatusInternalServerError).SendString("Could not save file: " + err.Error())
	}
	log.Printf("[Upload] ✅ File saved successfully: %s", filePath)

	videoID, fingerprint, err := vc.VideoService.SaveVideo(c, filePath)
	if err != nil {
		log.Printf("[Upload] ❌ Error saving video: %v", err)
		return c.Status(fiber.StatusInternalServerError).SendString("Error saving video: " + err.Error())
	}
	log.Printf("[Upload] ✅ Video saved successfully: videoID=%d, fingerprint=%s", videoID, fingerprint)

	go func(videoID int, filePath, filename string) {
		log.Printf("[AI] ⏳ Starting AI processing for videoID=%d, filePath=%s", videoID, filePath)
		aiResp, err := vc.AIServiceClient.ProcessVideo(filePath)
		if err != nil {
			log.Printf("[AI] ❌ Error processing video with AI: %v", err)
			return
		}
		log.Printf("[AI] ✅ Analysis complete: videoID=%d, match_score=%.2f, ai_hash=%s, metadata=%v",
			videoID, aiResp.MatchScore, aiResp.ComputedHash, aiResp.Metadata)

		threshold := 85.0
		if aiResp.MatchScore >= threshold {
			piracyURL := "https://example.com/pirated/" + filename
			log.Printf("[AI] 🚨 Piracy detected! VideoID=%d, Match Score=%.2f, URL: %s", videoID, aiResp.MatchScore, piracyURL)
		}
	}(videoID, filePath, fileHeader.Filename)

	log.Printf("[Upload] ✅ Responding with: id=%d, filename=%s, fingerprint=%s", videoID, fileHeader.Filename, fingerprint)
	return c.JSON(fiber.Map{
		"id":          videoID,
		"filename":    fileHeader.Filename,
		"fingerprint": fingerprint,
	})
}
