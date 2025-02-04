package services

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"io"
	"os"
	"path/filepath"

	"github.com/gofiber/fiber/v2"
	"github.com/jackc/pgx/v4/pgxpool"
)

type VideoService struct {
	DB         *pgxpool.Pool
	UploadsDir string
}

func NewVideoService(db *pgxpool.Pool, uploadsDir string) *VideoService {
	return &VideoService{DB: db, UploadsDir: uploadsDir}
}

func (vs *VideoService) SaveVideo(c *fiber.Ctx, filePath, name, description string) (int, string, error) {
    filename := filepath.Base(filePath)

    fingerprint, err := generateMD5(filePath)
    if err != nil {
        return 0, "", err
    }

    var videoID int
    err = vs.DB.QueryRow(context.Background(),
        "INSERT INTO uploaded_videos (filename, fingerprint, description) VALUES ($1, $2, $3) RETURNING id",
        filename, fingerprint, description).Scan(&videoID)
    if err != nil {
        return 0, "", err
    }

    return videoID, fingerprint, nil
}

func generateMD5(filePath string) (string, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	hasher := md5.New()
	if _, err := io.Copy(hasher, f); err != nil {
		return "", err
	}
	return hex.EncodeToString(hasher.Sum(nil)), nil
}
