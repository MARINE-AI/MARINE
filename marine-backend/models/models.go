package models

import "time"

type Video struct {
	ID            int       `json:"id"`
	UserEmail     string    `json:"user_email"`
	Filename      string    `json:"filename"`
	Title         string    `json:"title,omitempty"`
	Description   string    `json:"description,omitempty"`
	Fingerprint   string    `json:"fingerprint,omitempty"`
	HashVector    []byte    `json:"hash_vector,omitempty"`
	AudioSpectrum []byte    `json:"audio_spectrum,omitempty"`
	CreatedAt     time.Time `json:"created_at"`
	Flagged       bool      `json:"flagged"`
}

type PiracyCase struct {
	ID         int       `json:"id"`
	VideoID    int       `json:"video_id"`
	PiracyURL  string    `json:"piracy_url"`
	MatchScore float64   `json:"match_score"`
	DetectedAt time.Time `json:"detected_at"`
}
