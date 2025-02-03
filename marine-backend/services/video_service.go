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

func (vs *VideoService) SaveVideo(c *fiber.Ctx) (int, string, error) {
	file, err := c.FormFile("file")
	if err != nil {
		return 0, "", err
	}

	os.MkdirAll(vs.UploadsDir, os.ModePerm)
	savePath := filepath.Join(vs.UploadsDir, file.Filename)
	if err := c.SaveFile(file, savePath); err != nil {
		return 0, "", err
	}

	fingerprint, err := generateMD5(savePath)
	if err != nil {
		return 0, "", err
	}

	var videoID int
	err = vs.DB.QueryRow(context.Background(),
		"INSERT INTO videos (filename, fingerprint) VALUES ($1, $2) RETURNING id",
		file.Filename, fingerprint).Scan(&videoID)
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
