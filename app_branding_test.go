package main

import (
	"bytes"
	"encoding/binary"
	"image"
	"image/color"
	"image/png"
	"os"
	"strings"
	"testing"
)

var inquiraBrandColors = []color.RGBA{
	{R: 0x17, G: 0x20, B: 0x33, A: 0xff},
	{R: 0x6f, G: 0x91, B: 0xdf, A: 0xff},
	{R: 0xd3, G: 0x7a, B: 0x43, A: 0xff},
	{R: 0xf7, G: 0xf5, B: 0xf0, A: 0xff},
}

func TestPackagedAppIconsUseInquiraBrandMark(t *testing.T) {
	t.Parallel()

	svg, err := os.ReadFile("frontend/src/assets/favicon.svg")
	if err != nil {
		t.Fatalf("read frontend brand mark: %v", err)
	}
	for _, hex := range []string{"#172033", "#6F91DF", "#D37A43", "#F7F5F0"} {
		if !strings.Contains(string(svg), hex) {
			t.Fatalf("frontend brand mark is missing color %s", hex)
		}
	}

	appIconFile, err := os.Open("build/appicon.png")
	if err != nil {
		t.Fatalf("open packaged app icon: %v", err)
	}
	defer appIconFile.Close()
	appIcon, err := png.Decode(appIconFile)
	if err != nil {
		t.Fatalf("decode packaged app icon: %v", err)
	}
	if bounds := appIcon.Bounds(); bounds.Dx() != 1024 || bounds.Dy() != 1024 {
		t.Fatalf("packaged app icon size = %v, want 1024x1024", bounds)
	}
	assertBrandPalette(t, appIcon, 200)

	windowsIcon, err := os.ReadFile("build/windows/icon.ico")
	if err != nil {
		t.Fatalf("read Windows app icon: %v", err)
	}
	largest := largestPNGFromICO(t, windowsIcon)
	if bounds := largest.Bounds(); bounds.Dx() != 256 || bounds.Dy() != 256 {
		t.Fatalf("largest Windows icon size = %v, want 256x256", bounds)
	}
	assertBrandPalette(t, largest, 10)
}

func assertBrandPalette(t *testing.T, imageValue image.Image, minimumMatches int) {
	t.Helper()
	for _, target := range inquiraBrandColors {
		matches := 0
		bounds := imageValue.Bounds()
		for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
			for x := bounds.Min.X; x < bounds.Max.X; x++ {
				actual := color.RGBAModel.Convert(imageValue.At(x, y)).(color.RGBA)
				if colorDistance(actual, target) <= 8 {
					matches++
				}
			}
		}
		if matches < minimumMatches {
			t.Errorf("packaged icon has %d pixels near %#v, want at least %d", matches, target, minimumMatches)
		}
	}
}

func colorDistance(left, right color.RGBA) int {
	absolute := func(value int) int {
		if value < 0 {
			return -value
		}
		return value
	}
	return absolute(int(left.R)-int(right.R)) +
		absolute(int(left.G)-int(right.G)) +
		absolute(int(left.B)-int(right.B))
}

func largestPNGFromICO(t *testing.T, encoded []byte) image.Image {
	t.Helper()
	if len(encoded) < 6 || binary.LittleEndian.Uint16(encoded[0:2]) != 0 || binary.LittleEndian.Uint16(encoded[2:4]) != 1 {
		t.Fatal("Windows icon does not have a valid ICO header")
	}
	count := int(binary.LittleEndian.Uint16(encoded[4:6]))
	var largest image.Image
	for index := 0; index < count; index++ {
		entryOffset := 6 + index*16
		if entryOffset+16 > len(encoded) {
			t.Fatal("Windows icon directory is truncated")
		}
		byteSize := int(binary.LittleEndian.Uint32(encoded[entryOffset+8 : entryOffset+12]))
		imageOffset := int(binary.LittleEndian.Uint32(encoded[entryOffset+12 : entryOffset+16]))
		if imageOffset < 0 || byteSize < 0 || imageOffset+byteSize > len(encoded) {
			t.Fatal("Windows icon image entry is invalid")
		}
		payload := encoded[imageOffset : imageOffset+byteSize]
		if !bytes.HasPrefix(payload, []byte("\x89PNG\r\n\x1a\n")) {
			continue
		}
		decoded, err := png.Decode(bytes.NewReader(payload))
		if err != nil {
			t.Fatalf("decode Windows icon image: %v", err)
		}
		if largest == nil || decoded.Bounds().Dx() > largest.Bounds().Dx() {
			largest = decoded
		}
	}
	if largest == nil {
		t.Fatal("Windows icon does not contain a PNG image")
	}
	return largest
}
