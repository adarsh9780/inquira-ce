package main

import (
	"embed"
	"encoding/json"
	"fmt"
	"os"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/mac"
)

//go:embed all:frontend/dist
var assets embed.FS

func main() {
	// Create an instance of the app structure
	app := NewApp()
	if len(os.Args) > 1 && os.Args[1] == "runtime-info" {
		payload, err := json.MarshalIndent(app.RuntimeDiagnostics(), "", "  ")
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		fmt.Println(string(payload))
		return
	}

	// Create application with options
	err := wails.Run(desktopApplicationOptions(app))

	if err != nil {
		println("Error:", err.Error())
	}
}

func desktopApplicationOptions(app *App) *options.App {
	return &options.App{
		Title:  "Inquira",
		Width:  1400,
		Height: 900,
		// Keep the full workspace usable at the 768-point width of a 9-inch iPad.
		MinWidth:  768,
		MinHeight: 600,
		// Wails leaves the macOS zoom control disabled when Mac options are nil.
		// Keep native resize, zoom, and fullscreen window affordances available.
		DisableResize: false,
		Mac: &mac.Options{
			DisableZoom: false,
		},
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		// Match the default warm canvas so the webview never flashes a dark frame.
		BackgroundColour: &options.RGBA{R: 251, G: 248, B: 242, A: 1},
		OnStartup:        app.startup,
		OnShutdown:       app.shutdown,
		Bind: []interface{}{
			app,
		},
	}
}
