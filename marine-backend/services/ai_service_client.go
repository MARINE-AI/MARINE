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
	MatchScore    float64                `json:"match_score"`
	ComputedHash  string                 `json:"computed_hash"`
	VideoMetadata map[string]interface{} `json:"video_metadata"`
	KafkaMessage  string                 `json:"kafka_message,omitempty"`
}

func (client *AIServiceClient) ProcessVideo(videoFilePath, userEmail, name, description string) (AIResponse, error) {
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

	if err := writer.WriteField("user_email", userEmail); err != nil {
		return result, err
	}
	if err := writer.WriteField("name", name); err != nil {
		return result, err
	}
	if err := writer.WriteField("description", description); err != nil {
		return result, err
	}

	if err := writer.Close(); err != nil {
		return result, err
	}

	req, err := http.NewRequest("POST", client.AIServiceURL+"/match-video", &b)
	if err != nil {
		return result, err
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())

	resp, err := client.HTTPClient.Do(req)
	if err != nil {
		return result, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var errMsg map[string]interface{}
		if err := json.NewDecoder(resp.Body).Decode(&errMsg); err != nil {
			return result, err
		}
		return result, &RequestError{StatusCode: resp.StatusCode, Message: errMsg["error"].(string)}
	}

	err = json.NewDecoder(resp.Body).Decode(&result)
	return result, err
}

type RequestError struct {
	StatusCode int
	Message    string
}

func (e *RequestError) Error() string {
	return e.Message
}
