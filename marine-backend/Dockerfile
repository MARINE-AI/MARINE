FROM golang:1.19-alpine AS builder

WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o marine-backend .

FROM scratch
COPY --from=builder /src/marine-backend /marine-backend
EXPOSE 8080
ENTRYPOINT ["/marine-backend"]
