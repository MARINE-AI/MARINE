package controllers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"sync"

	"github.com/gofiber/fiber/v2"
)

var (
	urlList []string
	mu      sync.Mutex
)

type URLRequest struct {
	URL string `json:"url"`
}

type CrawlerController struct{}

func NewCrawlerController() *CrawlerController {
	return &CrawlerController{}
}

func (cc *CrawlerController) SubmitURL(c *fiber.Ctx) error {
	var req URLRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "Invalid request body",
		})
	}

	mu.Lock()
	urlList = append(urlList, req.URL)
	mu.Unlock()

	relayPayload, err := json.Marshal(req)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "Failed to marshal request",
		})
	}

	relayResp, err := http.Post("http://localhost:8001/submit", "application/json", bytes.NewReader(relayPayload))
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": fmt.Sprintf("Error relaying to crawler: %v", err),
		})
	}
	defer relayResp.Body.Close()

	body, err := ioutil.ReadAll(relayResp.Body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "Error reading crawler response",
		})
	}

	startResp, err := http.Get("http://localhost:8001/start_crawling")
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": fmt.Sprintf("Error triggering crawler: %v", err),
		})
	}
	defer startResp.Body.Close()

	startBody, err := ioutil.ReadAll(startResp.Body)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
			"error": "Error reading start crawler response",
		})
	}

	return c.JSON(fiber.Map{
		"message": fmt.Sprintf("URL %s submitted for crawling. Crawler response: %s. Start response: %s", req.URL, string(body), string(startBody)),
	})
}

func (cc *CrawlerController) StartCrawling(c *fiber.Ctx) error {
	mu.Lock()
	if len(urlList) == 0 {
		mu.Unlock()
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "No URLs submitted.",
		})
	}
	urlsToCrawl := make([]string, len(urlList))
	copy(urlsToCrawl, urlList)
	urlList = []string{}
	mu.Unlock()

	return c.JSON(fiber.Map{
		"message": fmt.Sprintf("Started crawling %d URLs.", len(urlsToCrawl)),
	})
}
