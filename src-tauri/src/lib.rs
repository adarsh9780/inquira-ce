use std::fs;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;

use serde::Deserialize;
use tauri::Emitter;
use tauri::Manager;

// ─────────────────────────────────────────────────────────────────────
// Configuration (parsed from inquira.toml)
// ─────────────────────────────────────────────────────────────────────

#[derive(Deserialize, Debug, Clone)]
struct InquiraConfig {
    python: Option<PythonConfig>,
    proxy: Option<ProxyConfig>,
    backend: Option<BackendConfig>,
}

#[derive(Deserialize, Debug, Clone)]
struct PythonConfig {
    version: Option<String>,
    #[serde(rename = "index-url")]
    index_url: Option<String>,
    #[serde(rename = "python-path")]
    python_path: Option<String>,
}

#[derive(Deserialize, Debug, Clone)]
struct ProxyConfig {
    #[serde(rename = "http-proxy")]
    http_proxy: Option<String>,
    #[serde(rename = "https-proxy")]
    https_proxy: Option<String>,
}

#[derive(Deserialize, Debug, Clone)]
struct BackendConfig {
    port: Option<u16>,
    host: Option<String>,
}

fn load_config(config_path: &PathBuf) -> InquiraConfig {
    if config_path.exists() {
        let content = fs::read_to_string(config_path).unwrap_or_default();
        toml::from_str(&content).unwrap_or(InquiraConfig {
            python: None,
            proxy: None,
            backend: None,
        })
    } else {
        InquiraConfig {
            python: None,
            proxy: None,
            backend: None,
        }
    }
}

// ─────────────────────────────────────────────────────────────────────
// Backend Process Manager
// ─────────────────────────────────────────────────────────────────────

struct BackendProcess(Mutex<Option<Child>>);

// ─────────────────────────────────────────────────────────────────────
// Tauri Commands (callable from frontend via invoke())
// ─────────────────────────────────────────────────────────────────────

#[tauri::command]
fn get_backend_url(app: tauri::AppHandle) -> String {
    let resource_dir = app
        .path()
        .resource_dir()
        .unwrap_or_else(|_| PathBuf::from("."));
    let config_path = resource_dir.join("inquira.toml");
    let config = load_config(&config_path);
    let port = config
        .backend
        .as_ref()
        .and_then(|b| b.port)
        .unwrap_or(8000);
    let host = config
        .backend
        .as_ref()
        .and_then(|b| b.host.clone())
        .unwrap_or_else(|| "localhost".to_string());
    format!("http://{}:{}", host, port)
}

// ─────────────────────────────────────────────────────────────────────
// UV Bootstrap Logic
// ─────────────────────────────────────────────────────────────────────

fn find_uv_binary(resource_dir: &PathBuf) -> PathBuf {
    // In production, UV is bundled in resources/
    let bundled = resource_dir.join("uv");
    if bundled.exists() {
        return bundled;
    }

    // In development, try to find uv on PATH
    if let Ok(output) = Command::new("which").arg("uv").output() {
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !path.is_empty() {
                return PathBuf::from(path);
            }
        }
    }

    // Fallback: assume it's on PATH
    PathBuf::from("uv")
}

fn bootstrap_python(
    uv_bin: &PathBuf,
    backend_dir: &PathBuf,
    venv_path: &PathBuf,
    config: &InquiraConfig,
) -> Result<(), String> {
    let python_version = config
        .python
        .as_ref()
        .and_then(|p| p.version.clone())
        .unwrap_or_else(|| "3.12".to_string());

    // Check if a custom python-path is configured
    if let Some(ref _custom_python) = config.python.as_ref().and_then(|p| p.python_path.clone()) {
        log::info!("Using custom Python path, skipping UV python install");
    } else {
        log::info!("Installing Python {} via UV...", python_version);
        let mut cmd = Command::new(uv_bin);
        cmd.args(["python", "install", &python_version]);
        apply_proxy_env(&mut cmd, config);
        let status = cmd.status().map_err(|e| format!("uv python install failed: {}", e))?;
        if !status.success() {
            return Err("uv python install returned non-zero exit code".to_string());
        }
    }

    log::info!("Syncing Python environment...");
    let mut cmd = Command::new(uv_bin);
    cmd.args(["sync", "--project", backend_dir.to_str().unwrap()])
        .env("UV_PROJECT_ENVIRONMENT", venv_path.to_str().unwrap());

    // Apply custom index URL if configured
    if let Some(ref index_url) = config.python.as_ref().and_then(|p| p.index_url.clone()) {
        cmd.env("UV_INDEX_URL", index_url);
    }

    apply_proxy_env(&mut cmd, config);
    let status = cmd.status().map_err(|e| format!("uv sync failed: {}", e))?;
    if !status.success() {
        return Err("uv sync returned non-zero exit code".to_string());
    }

    Ok(())
}

fn apply_proxy_env(cmd: &mut Command, config: &InquiraConfig) {
    if let Some(ref proxy) = config.proxy {
        if let Some(ref http) = proxy.http_proxy {
            cmd.env("HTTP_PROXY", http);
        }
        if let Some(ref https) = proxy.https_proxy {
            cmd.env("HTTPS_PROXY", https);
        }
    }
}

fn start_backend(
    uv_bin: &PathBuf,
    backend_dir: &PathBuf,
    venv_path: &PathBuf,
    config: &InquiraConfig,
) -> Result<Child, String> {
    let port = config
        .backend
        .as_ref()
        .and_then(|b| b.port)
        .unwrap_or(8000);

    log::info!("Starting Inquira backend on port {}...", port);

    let mut cmd = Command::new(uv_bin);
    cmd.args([
        "run",
        "--project",
        backend_dir.to_str().unwrap(),
        "python",
        "-m",
        "app.main",
    ])
    .current_dir(backend_dir)
    .env("UV_PROJECT_ENVIRONMENT", venv_path.to_str().unwrap())
    .env("INQUIRA_PORT", port.to_string())
    .env("INQUIRA_DESKTOP", "1");

    apply_proxy_env(&mut cmd, config);

    let child = cmd
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

    Ok(child)
}

// ─────────────────────────────────────────────────────────────────────
// App Entry Point
// ─────────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // Set up logging in debug mode
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Resolve paths
            let resource_dir = app
                .path()
                .resource_dir()
                .unwrap_or_else(|_| PathBuf::from("."));
            let data_dir = app.path().app_data_dir().unwrap_or_else(|_| {
                dirs_next::home_dir()
                    .unwrap_or_else(|| PathBuf::from("."))
                    .join(".inquira")
            });
            fs::create_dir_all(&data_dir).ok();

            let config_path = resource_dir.join("inquira.toml");
            let config = load_config(&config_path);

            let uv_bin = find_uv_binary(&resource_dir);
            // In dev, backend is a sibling directory; in prod, it's bundled in resources
            let backend_dir = if cfg!(debug_assertions) {
                PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend")
            } else {
                resource_dir.join("backend")
            };
            let venv_path = data_dir.join(".venv");

            // Phase 1: Bootstrap Python + venv (one-time)
            if !venv_path.exists() {
                log::info!("First launch detected. Bootstrapping Python environment...");
                app.emit("backend-status", "Installing Python environment (one-time setup)...")
                    .ok();

                if let Err(e) = bootstrap_python(&uv_bin, &backend_dir, &venv_path, &config) {
                    log::error!("Python bootstrap failed: {}", e);
                    app.emit("backend-status", &format!("Setup failed: {}", e))
                        .ok();
                    // Don't crash — let the user see the error in the UI
                    return Ok(());
                }
            }

            // Phase 2: Start the backend
            app.emit("backend-status", "Starting backend...").ok();
            match start_backend(&uv_bin, &backend_dir, &venv_path, &config) {
                Ok(child) => {
                    log::info!("Backend process started (PID: {})", child.id());
                    let state = app.state::<BackendProcess>();
                    *state.0.lock().unwrap() = Some(child);
                    app.emit("backend-status", "ready").ok();
                }
                Err(e) => {
                    log::error!("Backend start failed: {}", e);
                    app.emit("backend-status", &format!("Backend failed: {}", e))
                        .ok();
                }
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_url])
        .build(tauri::generate_context!())
        .expect("error while building Inquira")
        .run(|app, event| {
            // Kill the backend process when the app exits
            if let tauri::RunEvent::Exit = event {
                if let Some(state) = app.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(ref mut child) = *guard {
                            log::info!("Shutting down backend process...");
                            let _ = child.kill();
                        }
                    }
                }
            }
        });
}
