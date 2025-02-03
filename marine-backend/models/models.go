package models

import "time"

type Video struct {
	ID          int       `json:"id"`
	Filename    string    `json:"filename"`
	Fingerprint string    `json:"fingerprint"`
	UploadedAt  time.Time `json:"uploaded_at"`
}

type PiracyCase struct {
	ID         int       `json:"id"`
	VideoID    int       `json:"video_id"`
	PiracyURL  string    `json:"piracy_url"`
	MatchScore float64   `json:"match_score"`
	DetectedAt time.Time `json:"detected_at"`
}
