package services

import (
	"bytes"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

type AIServiceClient struct {
	AIServiceURL string
	HTTPClient   *http.Client
}

func NewAIServiceClient(aiServiceURL string) *AIServiceClient {
	return &AIServiceClient{
		AIServiceURL: aiServiceURL,
		HTTPClient:   &http.Client{Timeout: 30 * time.Second},
	}
}

type AIResponse struct {
	MatchScore   float64 `json:"match_score"`
	ComputedHash string  `json:"computed_hash"`
	Metadata     map[string]interface{} `json:"metadata"`
}

func (client *AIServiceClient) ProcessVideo(videoFilePath string) (AIResponse, error) {
	var result AIResponse

	file, err := os.Open(videoFilePath)
	if err != nil {
		return result, err
	}
	defer file.Close()

	var b bytes.Buffer
	writer := multipart.NewWriter(&b)
	part, err := writer.CreateFormFile("video_file", filepath.Base(videoFilePath))
	if err != nil {
		return result, err
	}
	if _, err := io.Copy(part, file); err != nil {
		return result, err
	}
	writer.Close()

	req, err := http.NewRequest("POST", client.AIServiceURL+"/compare-videos", &b)
	if err != nil {
		return result, err
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())

	resp, err := client.HTTPClient.Do(req)
	if err != nil {
		return result, err
	}
	defer resp.Body.Close()

	err = json.NewDecoder(resp.Body).Decode(&result)
	return result, err
}
