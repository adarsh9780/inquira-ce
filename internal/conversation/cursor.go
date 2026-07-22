package conversation

import (
	"encoding/base64"
	"encoding/json"
	"errors"
)

type turnCursor struct {
	Sequence int    `json:"sequence"`
	TurnID   string `json:"turn_id"`
}

func encodeTurnCursor(turn Turn) string {
	payload, _ := json.Marshal(turnCursor{Sequence: turn.Sequence, TurnID: turn.ID})
	return base64.RawURLEncoding.EncodeToString(payload)
}

func decodeTurnCursor(value string) (turnCursor, error) {
	payload, err := base64.RawURLEncoding.DecodeString(value)
	if err != nil {
		return turnCursor{}, err
	}
	var cursor turnCursor
	if err := json.Unmarshal(payload, &cursor); err != nil {
		return turnCursor{}, err
	}
	if cursor.Sequence < 1 || cursor.TurnID == "" {
		return turnCursor{}, errors.New("invalid turn cursor")
	}
	return cursor, nil
}
