package controllers

import (
	"bytes"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"

	"marine-backend/services"

	"github.com/gofiber/fiber/v2"
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

	videoName := c.FormValue("name")
	videoDescription := c.FormValue("description")
	userEmail := c.FormValue("user_email")

	filePath := vc.VideoService.UploadsDir + "/" + fileHeader.Filename
	log.Printf("[Upload] 📂 File will be saved to: %s", filePath)
	if err := c.SaveFile(fileHeader, filePath); err != nil {
		log.Printf("[Upload] ❌ Error saving file to disk: %v", err)
		return c.Status(fiber.StatusInternalServerError).SendString("Could not save file: " + err.Error())
	}
	log.Printf("[Upload] ✅ File saved successfully: %s", filePath)

	videoID, fingerprint, err := vc.VideoService.SaveVideo(c, filePath, videoName, videoDescription, userEmail)
	if err != nil {
		log.Printf("[Upload] ❌ Error saving video: %v", err)
		return c.Status(fiber.StatusInternalServerError).SendString("Error saving video: " + err.Error())
	}
	log.Printf("[Upload] ✅ Video saved successfully: videoID=%d, fingerprint=%s", videoID, fingerprint)

	go func(videoID int, filePath, filename, userEmail, name, description string) {
		defer func() {
			if r := recover(); r != nil {
				log.Printf("[AI] ❌ Recovered from panic: %v", r)
			}
		}()

		log.Printf("[AI] ⏳ Starting AI processing for videoID=%d, filePath=%s", videoID, filePath)
		aiResp, err := vc.AIServiceClient.ProcessVideo(filePath, userEmail, name, description)
		if err != nil {
			log.Printf("[AI] ❌ Error processing video with AI: %v", err)
			return
		}
		log.Printf("[AI] ✅ Analysis complete: videoID=%d, match_score=%.2f, ai_hash=%s, video_metadata=%v",
			videoID, aiResp.MatchScore, aiResp.ComputedHash, aiResp.VideoMetadata)

		threshold := 85.0
		if aiResp.MatchScore >= threshold {
			piracyURL := "https://example.com/pirated/" + filename
			log.Printf("[AI] 🚨 Piracy detected! VideoID=%d, Match Score=%.2f, URL: %s", videoID, aiResp.MatchScore, piracyURL)
		}
	}(videoID, filePath, fileHeader.Filename, userEmail, videoName, videoDescription)

	go func(videoID int, filePath, filename, name, description string) {
		defer func() {
			if r := recover(); r != nil {
				log.Printf("[Discovery] ❌ Recovered from panic: %v", r)
			}
		}()

		discoveryURL := "http://localhost:8002/discover"

		file, err := os.Open(filePath)
		if err != nil {
			log.Printf("[Discovery] ❌ Error opening file: %v", err)
			return
		}
		defer file.Close()

		var b bytes.Buffer
		writer := multipart.NewWriter(&b)
		part, err := writer.CreateFormFile("file", filename)
		if err != nil {
			log.Printf("[Discovery] ❌ Error creating form file: %v", err)
			return
		}
		if _, err := io.Copy(part, file); err != nil {
			log.Printf("[Discovery] ❌ Error copying file: %v", err)
			return
		}
		if err := writer.WriteField("name", name); err != nil {
			log.Printf("[Discovery] ❌ Error writing field 'name': %v", err)
			return
		}
		if err := writer.WriteField("description", description); err != nil {
			log.Printf("[Discovery] ❌ Error writing field 'description': %v", err)
			return
		}
		if err := writer.Close(); err != nil {
			log.Printf("[Discovery] ❌ Error closing writer: %v", err)
			return
		}

		req, err := http.NewRequest("POST", discoveryURL, &b)
		if err != nil {
			log.Printf("[Discovery] ❌ Error creating request: %v", err)
			return
		}
		req.Header.Set("Content-Type", writer.FormDataContentType())

		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			log.Printf("[Discovery] ❌ Error sending request: %v", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			log.Printf("[Discovery] ❌ Discovery service returned status: %d", resp.StatusCode)
			return
		}
		log.Printf("[Discovery] ✅ Successfully sent video to discovery service for videoID=%d", videoID)
	}(videoID, filePath, fileHeader.Filename, videoName, videoDescription)

	return c.JSON(fiber.Map{
		"id":          videoID,
		"filename":    fileHeader.Filename,
		"fingerprint": fingerprint,
	})
}
