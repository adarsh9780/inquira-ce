use std::collections::HashMap;
use std::fs;
use std::fs::OpenOptions;
use std::hash::{DefaultHasher, Hash, Hasher};
use std::io::{Read, Write};
use std::net::TcpListener;
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child as StdChild, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use portable_pty::{native_pty_system, CommandBuilder, PtySize};
use serde::{Deserialize, Serialize};
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
    execution: Option<ExecutionConfig>,
    agent_service: Option<AgentServiceConfig>,
    logging: Option<LoggingConfig>,
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

#[derive(Deserialize, Debug, Clone)]
struct ExecutionConfig {
    provider: Option<String>,
}

#[derive(Deserialize, Debug, Clone)]
struct AgentServiceConfig {
    host: Option<String>,
    port: Option<u16>,
    path: Option<String>,
    command: Option<String>,
    startup_timeout_sec: Option<u64>,
}

#[derive(Deserialize, Debug, Clone)]
struct LoggingConfig {
    console_level: Option<String>,
}

fn load_config(config_path: &PathBuf) -> InquiraConfig {
    if config_path.exists() {
        let content = fs::read_to_string(config_path).unwrap_or_default();
        match toml::from_str::<InquiraConfig>(&content) {
            Ok(cfg) => cfg,
            Err(e) => {
                log::error!(
                    "Failed to parse inquira.toml at {}: {}",
                    config_path.display(),
                    e
                );
                InquiraConfig {
                    python: None,
                    proxy: None,
                    backend: None,
                    execution: None,
                    agent_service: None,
                    logging: None,
                }
            }
        }
    } else {
        InquiraConfig {
            python: None,
            proxy: None,
            backend: None,
            execution: None,
            agent_service: None,
            logging: None,
        }
    }
}

fn resolve_resource_path(resource_dir: &PathBuf, relative: &str) -> PathBuf {
    let direct = resource_dir.join(relative);
    if direct.exists() {
        return direct;
    }
    resource_dir.join("_up_").join(relative)
}

fn normalize_console_level(raw: &str) -> String {
    match raw.trim().to_uppercase().as_str() {
        "TRACE" => "TRACE".to_string(),
        "DEBUG" => "DEBUG".to_string(),
        "INFO" => "INFO".to_string(),
        "WARNING" => "WARNING".to_string(),
        "ERROR" => "ERROR".to_string(),
        "CRITICAL" => "CRITICAL".to_string(),
        _ => "ERROR".to_string(),
    }
}

fn resolve_shared_console_log_level(config: &InquiraConfig) -> String {
    if let Ok(value) = std::env::var("INQUIRA_LOG_CONSOLE_LEVEL") {
        if !value.trim().is_empty() {
            return normalize_console_level(&value);
        }
    }
    if let Some(value) = config
        .logging
        .as_ref()
        .and_then(|l| l.console_level.clone())
        .filter(|v| !v.trim().is_empty())
    {
        return normalize_console_level(&value);
    }
    "ERROR".to_string()
}

fn startup_log_paths(data_dir: &Path) -> StartupLogPaths {
    let log_dir = data_dir.join("logs");
    StartupLogPaths {
        desktop: log_dir.join("desktop-startup.log"),
        backend: log_dir.join("backend-startup.log"),
        agent: log_dir.join("agent-startup.log"),
    }
}

#[cfg_attr(not(target_os = "windows"), allow(dead_code))]
fn vc_redist_marker_path(data_dir: &Path) -> PathBuf {
    data_dir.join(".vc_redist_installed")
}

#[cfg_attr(not(target_os = "windows"), allow(dead_code))]
fn vc_redist_installer_path(data_dir: &Path) -> PathBuf {
    data_dir.join("bootstrap").join("vc_redist.x64.exe")
}

#[cfg_attr(not(target_os = "windows"), allow(dead_code))]
fn vc_redist_download_url() -> &'static str {
    "https://aka.ms/vc14/vc_redist.x64.exe"
}

#[cfg_attr(not(target_os = "windows"), allow(dead_code))]
fn vc_redist_success_exit_code(code: i32) -> bool {
    matches!(code, 0 | 1638 | 3010)
}

fn append_startup_log(log_path: &Path, message: &str) {
    if let Some(parent) = log_path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
        let _ = writeln!(file, "{}", message);
    }
}

#[cfg(target_os = "windows")]
fn ensure_windows_vc_redist(
    data_dir: &Path,
    desktop_log_path: &Path,
    config: &InquiraConfig,
    app: &tauri::AppHandle,
) -> Result<(), String> {
    let marker_path = vc_redist_marker_path(data_dir);
    if marker_path.exists() {
        return Ok(());
    }

    let installer_path = vc_redist_installer_path(data_dir);
    if let Some(parent) = installer_path.parent() {
        fs::create_dir_all(parent).map_err(|e| {
            format!(
                "Failed to create VC++ bootstrap directory {}: {}",
                parent.display(),
                e
            )
        })?;
    }

    emit_startup_message(
        app,
        "Installing Microsoft Visual C++ runtime (one-time setup)...",
    );
    append_startup_log(
        desktop_log_path,
        &format!(
            "VC++ runtime missing. Downloading installer from {} to {}",
            vc_redist_download_url(),
            installer_path.display()
        ),
    );

    let mut download_cmd = Command::new("powershell.exe");
    download_cmd.args([
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        &format!(
            "Invoke-WebRequest -Uri '{}' -OutFile '{}'",
            vc_redist_download_url(),
            installer_path.display()
        ),
    ]);
    apply_proxy_env(&mut download_cmd, config);
    redirect_command_output(
        &mut download_cmd,
        desktop_log_path,
        "vc_redist_download",
        &format!(
            "powershell Invoke-WebRequest {} -> {}",
            vc_redist_download_url(),
            installer_path.display()
        ),
        data_dir,
    )?;
    let download_status = download_cmd.status().map_err(|e| {
        format!(
            "Failed to download Microsoft Visual C++ runtime installer: {}",
            e
        )
    })?;
    if !download_status.success() || !installer_path.exists() {
        return Err(format!(
            "Microsoft Visual C++ runtime download failed (status: {:?}). See {}",
            download_status.code(),
            desktop_log_path.display()
        ));
    }

    append_startup_log(
        desktop_log_path,
        &format!(
            "Running Microsoft Visual C++ runtime installer from {}",
            installer_path.display()
        ),
    );
    let mut install_cmd = Command::new(&installer_path);
    install_cmd.args(["/install", "/quiet", "/norestart"]);
    redirect_command_output(
        &mut install_cmd,
        desktop_log_path,
        "vc_redist_install",
        &format!("{} /install /quiet /norestart", installer_path.display()),
        data_dir,
    )?;
    let install_status = install_cmd.status().map_err(|e| {
        format!(
            "Failed to run Microsoft Visual C++ runtime installer: {}",
            e
        )
    })?;
    let exit_code = install_status.code().unwrap_or(-1);
    if !vc_redist_success_exit_code(exit_code) {
        return Err(format!(
            "Microsoft Visual C++ runtime installer failed with exit code {}. See {}",
            exit_code,
            desktop_log_path.display()
        ));
    }

    let marker_contents = if exit_code == 3010 {
        "installed=reboot_required\n"
    } else {
        "installed=ok\n"
    };
    fs::write(&marker_path, marker_contents).map_err(|e| {
        format!(
            "Microsoft Visual C++ runtime installed, but failed to write marker {}: {}",
            marker_path.display(),
            e
        )
    })?;

    if exit_code == 3010 {
        append_startup_log(
            desktop_log_path,
            "Microsoft Visual C++ runtime install completed and requested a reboot.",
        );
    } else {
        append_startup_log(
            desktop_log_path,
            "Microsoft Visual C++ runtime install completed successfully.",
        );
    }

    Ok(())
}

#[cfg(not(target_os = "windows"))]
fn ensure_windows_vc_redist(
    _data_dir: &Path,
    _desktop_log_path: &Path,
    _config: &InquiraConfig,
    _app: &tauri::AppHandle,
) -> Result<(), String> {
    Ok(())
}

fn start_log_session(log_path: &Path, process_name: &str, command_summary: &str, cwd: &Path) {
    append_startup_log(log_path, "");
    append_startup_log(
        log_path,
        "============================================================",
    );
    append_startup_log(log_path, &format!("process={process_name}"));
    append_startup_log(log_path, &format!("cwd={}", cwd.display()));
    append_startup_log(log_path, &format!("command={command_summary}"));
}

fn redirect_command_output(
    cmd: &mut Command,
    log_path: &Path,
    process_name: &str,
    command_summary: &str,
    cwd: &Path,
) -> Result<(), String> {
    start_log_session(log_path, process_name, command_summary, cwd);
    let stdout_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
        .map_err(|e| {
            format!(
                "Failed to open {process_name} startup log at {}: {e}",
                log_path.display()
            )
        })?;
    let stderr_file = stdout_file.try_clone().map_err(|e| {
        format!(
            "Failed to clone {process_name} startup log handle at {}: {e}",
            log_path.display()
        )
    })?;
    cmd.stdout(Stdio::from(stdout_file));
    cmd.stderr(Stdio::from(stderr_file));
    Ok(())
}

// ─────────────────────────────────────────────────────────────────────
// Backend Process Manager
// ─────────────────────────────────────────────────────────────────────

struct BackendProcess(Mutex<Option<StdChild>>);
struct AgentProcess(Mutex<Option<StdChild>>);

struct PtySession {
    writer: Box<dyn Write + Send>,
    child: Box<dyn portable_pty::Child + Send>,
    master: Box<dyn portable_pty::MasterPty + Send>,
}

struct PtySessions(Mutex<HashMap<String, PtySession>>);

#[derive(Serialize, Clone, Default)]
struct StartupSnapshot {
    ready: bool,
    error: String,
    message: String,
}

struct StartupState(Mutex<StartupSnapshot>);

#[derive(Clone, Debug, PartialEq, Eq)]
struct StartupLogPaths {
    desktop: PathBuf,
    backend: PathBuf,
    agent: PathBuf,
}

#[derive(Serialize)]
struct PtyStartResponse {
    session_id: String,
    cwd: String,
    shell: String,
}

#[derive(Serialize, Clone)]
struct PtyDataEvent {
    session_id: String,
    data: String,
}

#[derive(Serialize, Clone)]
struct PtyExitEvent {
    session_id: String,
}

#[derive(Serialize)]
struct PtyStopResponse {
    stopped: bool,
}

#[derive(Serialize)]
struct AuthLoopbackResponse {
    redirect_url: String,
}

fn stop_child_process(name: &str, child: &mut StdChild) {
    const GRACEFUL_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(3);
    const GRACEFUL_SHUTDOWN_POLL_INTERVAL: Duration = Duration::from_millis(100);

    match child.try_wait() {
        Ok(Some(status)) => {
            log::info!("{name} process already exited with status: {status}");
            return;
        }
        Ok(None) => {}
        Err(e) => {
            log::warn!("Failed to check {name} process status before shutdown: {e}");
        }
    }

    #[cfg(unix)]
    {
        let pid = child.id().to_string();
        match Command::new("kill").args(["-TERM", &pid]).status() {
            Ok(status) if status.success() => {
                let started = Instant::now();
                loop {
                    match child.try_wait() {
                        Ok(Some(status)) => {
                            log::info!("{name} process exited gracefully with status: {status}");
                            return;
                        }
                        Ok(None) => {
                            if started.elapsed() >= GRACEFUL_SHUTDOWN_TIMEOUT {
                                break;
                            }
                            thread::sleep(GRACEFUL_SHUTDOWN_POLL_INTERVAL);
                        }
                        Err(e) => {
                            log::warn!("Failed while waiting for graceful {name} shutdown: {e}");
                            break;
                        }
                    }
                }
                log::warn!(
                    "{name} process did not exit after SIGTERM within {:?}; force-killing.",
                    GRACEFUL_SHUTDOWN_TIMEOUT
                );
            }
            Ok(status) => {
                log::warn!(
                    "Failed to send SIGTERM to {name} process (exit status: {status}); force-killing."
                );
            }
            Err(e) => {
                log::warn!("Failed to send SIGTERM to {name} process: {e}; force-killing.");
            }
        }
    }

    if let Err(e) = child.kill() {
        log::warn!("Failed to kill {name} process: {e}");
    }
    if let Err(e) = child.wait() {
        log::warn!("Failed to wait for {name} process exit: {e}");
    }
}

fn stop_agent_process(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<AgentProcess>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(mut child) = guard.take() {
                log::info!("Shutting down agent runtime process...");
                stop_child_process("agent runtime", &mut child);
            }
        }
    }
}

fn stop_backend_process(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<BackendProcess>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(mut child) = guard.take() {
                log::info!("Shutting down backend process...");
                stop_child_process("backend", &mut child);
            }
        }
    }
}

fn update_startup_state(
    app: &tauri::AppHandle,
    ready: bool,
    error: impl Into<String>,
    message: impl Into<String>,
) {
    if let Some(state) = app.try_state::<StartupState>() {
        if let Ok(mut guard) = state.0.lock() {
            *guard = StartupSnapshot {
                ready,
                error: error.into(),
                message: message.into(),
            };
        }
    }
}

fn emit_startup_message(app: &tauri::AppHandle, message: impl Into<String>) {
    let rendered = message.into();
    update_startup_state(app, false, "", rendered.clone());
    let _ = app.emit("backend-status", rendered);
}

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

// ─────────────────────────────────────────────────────────────────────
// Tauri Commands (callable from frontend via invoke())
// ─────────────────────────────────────────────────────────────────────

#[tauri::command]
fn get_backend_url(app: tauri::AppHandle) -> String {
    let resource_dir = app
        .path()
        .resource_dir()
        .unwrap_or_else(|_| PathBuf::from("."));
    let config_path = resolve_resource_path(&resource_dir, "inquira.toml");
    let config = load_config(&config_path);
    let port = config.backend.as_ref().and_then(|b| b.port).unwrap_or(8000);
    let host = config
        .backend
        .as_ref()
        .and_then(|b| b.host.clone())
        .unwrap_or_else(|| "localhost".to_string());
    format!("http://{}:{}", host, port)
}

#[tauri::command]
fn get_startup_state(app: tauri::AppHandle) -> StartupSnapshot {
    app.try_state::<StartupState>()
        .and_then(|state| state.0.lock().ok().map(|guard| guard.clone()))
        .unwrap_or_default()
}

#[tauri::command]
fn open_external_url(url: String) -> Result<(), String> {
    let value = url.trim();
    if value.is_empty() {
        return Err("URL is required.".to_string());
    }
    let lower = value.to_lowercase();
    if !(lower.starts_with("http://") || lower.starts_with("https://")) {
        return Err("Only http(s) links can be opened externally.".to_string());
    }

    #[cfg(target_os = "macos")]
    let mut command = {
        let mut cmd = Command::new("open");
        cmd.arg(value);
        cmd
    };

    #[cfg(target_os = "linux")]
    let mut command = {
        let mut cmd = Command::new("xdg-open");
        cmd.arg(value);
        cmd
    };

    #[cfg(target_os = "windows")]
    let mut command = {
        let mut cmd = Command::new("rundll32");
        cmd.args(["url.dll,FileProtocolHandler", value]);
        cmd
    };

    command
        .spawn()
        .map(|_| ())
        .map_err(|error| format!("Failed to open URL: {error}"))
}

#[tauri::command]
fn auth_start_loopback_listener(app: tauri::AppHandle) -> Result<AuthLoopbackResponse, String> {
    let listener = TcpListener::bind("127.0.0.1:0")
        .map_err(|error| format!("Failed to bind auth callback listener: {error}"))?;
    let address = listener
        .local_addr()
        .map_err(|error| format!("Failed to inspect auth callback listener: {error}"))?;
    let redirect_url = format!("http://127.0.0.1:{}/auth/callback", address.port());
    let app_handle = app.clone();

    thread::spawn(move || {
        if let Ok((mut stream, _peer)) = listener.accept() {
            let mut buffer = [0_u8; 4096];
            let read_len = stream.read(&mut buffer).unwrap_or(0);
            let request = String::from_utf8_lossy(&buffer[..read_len]);
            let request_line = request.lines().next().unwrap_or_default();
            let target = request_line.split_whitespace().nth(1).unwrap_or_default();
            let query = target
                .split_once('?')
                .map(|(_, raw)| raw)
                .unwrap_or_default();
            let params: HashMap<String, String> = url::form_urlencoded::parse(query.as_bytes())
                .into_owned()
                .collect();
            let code = params.get("code").cloned().unwrap_or_default();
            let error = params.get("error").cloned().unwrap_or_default();
            let error_description = params.get("error_description").cloned().unwrap_or_default();

            let body = if code.is_empty() {
                let _ = app_handle.emit(
                    "auth:callback",
                    serde_json::json!({
                        "code": "",
                        "error": error,
                        "error_description": error_description,
                    }),
                );
                "<html><body><h2>Inquira sign-in failed.</h2><p>You can close this window and try again.</p></body></html>"
            } else {
                let _ = app_handle.emit(
                    "auth:callback",
                    serde_json::json!({
                        "code": code,
                        "error": error,
                        "error_description": error_description,
                    }),
                );
                "<html><body><h2>Inquira sign-in complete.</h2><p>You can close this window and return to the app.</p></body></html>"
            };

            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                body.len(),
                body
            );
            let _ = stream.write_all(response.as_bytes());
            let _ = stream.flush();
        }
    });

    Ok(AuthLoopbackResponse { redirect_url })
}

fn detect_default_shell() -> (String, Vec<String>) {
    if cfg!(target_os = "windows") {
        let shell = std::env::var("COMSPEC")
            .ok()
            .filter(|v| !v.trim().is_empty())
            .unwrap_or_else(|| "powershell.exe".to_string());
        return (shell, Vec::new());
    }

    let shell = std::env::var("SHELL")
        .ok()
        .filter(|v| !v.trim().is_empty())
        .unwrap_or_else(|| "/bin/bash".to_string());
    (shell, Vec::new())
}

fn resolve_pty_cwd(requested_cwd: Option<String>) -> String {
    let fallback = std::env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .to_string_lossy()
        .to_string();
    let Some(raw) = requested_cwd else {
        return fallback;
    };
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return fallback;
    }
    let candidate = PathBuf::from(trimmed);
    if candidate.exists() && candidate.is_dir() {
        return candidate.to_string_lossy().to_string();
    }
    fallback
}

fn emit_terminal_exit_event(app: &tauri::AppHandle, session_id: &str) {
    let _ = app.emit(
        "terminal:pty-exit",
        PtyExitEvent {
            session_id: session_id.to_string(),
        },
    );
}

#[tauri::command]
fn tauri_terminal_start(
    app: tauri::AppHandle,
    sessions: tauri::State<PtySessions>,
    session_id: String,
    cwd: Option<String>,
    cols: u16,
    rows: u16,
) -> Result<PtyStartResponse, String> {
    let normalized_session_id = session_id.trim().to_string();
    if normalized_session_id.is_empty() {
        return Err("session_id is required".to_string());
    }

    {
        let mut guard = sessions
            .0
            .lock()
            .map_err(|_| "Failed to lock PTY session store.".to_string())?;
        if let Some(mut existing) = guard.remove(&normalized_session_id) {
            let _ = existing.child.kill();
            emit_terminal_exit_event(&app, &normalized_session_id);
        }
    }

    let shell_cwd = resolve_pty_cwd(cwd);
    let pty_rows = rows.max(1);
    let pty_cols = cols.max(1);
    let pty_system = native_pty_system();
    let pair = pty_system
        .openpty(PtySize {
            rows: pty_rows,
            cols: pty_cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|err| format!("Unable to allocate PTY: {err}"))?;

    let (shell, args) = detect_default_shell();
    let mut cmd = CommandBuilder::new(&shell);
    for arg in &args {
        cmd.arg(arg);
    }
    cmd.cwd(&shell_cwd);

    let child = pair
        .slave
        .spawn_command(cmd)
        .map_err(|err| format!("Unable to start shell: {err}"))?;
    let mut reader = pair
        .master
        .try_clone_reader()
        .map_err(|err| format!("Unable to clone PTY reader: {err}"))?;
    let writer = pair
        .master
        .take_writer()
        .map_err(|err| format!("Unable to open PTY writer: {err}"))?;

    let app_handle = app.clone();
    let session_for_thread = normalized_session_id.clone();
    std::thread::spawn(move || {
        let mut buf = [0_u8; 4096];
        loop {
            match reader.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    let chunk = String::from_utf8_lossy(&buf[..n]).to_string();
                    let _ = app_handle.emit(
                        "terminal:pty-data",
                        PtyDataEvent {
                            session_id: session_for_thread.clone(),
                            data: chunk,
                        },
                    );
                }
                Err(_) => break,
            }
        }
        emit_terminal_exit_event(&app_handle, &session_for_thread);
    });

    let session = PtySession {
        writer,
        child,
        master: pair.master,
    };

    let mut guard = sessions
        .0
        .lock()
        .map_err(|_| "Failed to lock PTY session store.".to_string())?;
    guard.insert(normalized_session_id.clone(), session);

    Ok(PtyStartResponse {
        session_id: normalized_session_id,
        cwd: shell_cwd,
        shell,
    })
}

#[tauri::command]
fn tauri_terminal_write(
    sessions: tauri::State<PtySessions>,
    session_id: String,
    data: String,
) -> Result<(), String> {
    let mut guard = sessions
        .0
        .lock()
        .map_err(|_| "Failed to lock PTY session store.".to_string())?;
    let session = guard
        .get_mut(&session_id)
        .ok_or_else(|| "PTY session not found.".to_string())?;
    session
        .writer
        .write_all(data.as_bytes())
        .map_err(|err| format!("Failed to write PTY input: {err}"))?;
    session
        .writer
        .flush()
        .map_err(|err| format!("Failed to flush PTY input: {err}"))?;
    Ok(())
}

#[tauri::command]
fn tauri_terminal_resize(
    sessions: tauri::State<PtySessions>,
    session_id: String,
    cols: u16,
    rows: u16,
) -> Result<(), String> {
    let mut guard = sessions
        .0
        .lock()
        .map_err(|_| "Failed to lock PTY session store.".to_string())?;
    let session = guard
        .get_mut(&session_id)
        .ok_or_else(|| "PTY session not found.".to_string())?;
    let pty_rows = rows.max(1);
    let pty_cols = cols.max(1);
    session
        .master
        .resize(PtySize {
            rows: pty_rows,
            cols: pty_cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|err| format!("Failed to resize PTY: {err}"))?;
    Ok(())
}

#[tauri::command]
fn tauri_terminal_stop(
    app: tauri::AppHandle,
    sessions: tauri::State<PtySessions>,
    session_id: String,
) -> Result<PtyStopResponse, String> {
    let mut guard = sessions
        .0
        .lock()
        .map_err(|_| "Failed to lock PTY session store.".to_string())?;
    if let Some(mut session) = guard.remove(&session_id) {
        let _ = session.child.kill();
        emit_terminal_exit_event(&app, &session_id);
        return Ok(PtyStopResponse { stopped: true });
    }
    Ok(PtyStopResponse { stopped: false })
}

// ─────────────────────────────────────────────────────────────────────
// UV Bootstrap Logic
// ─────────────────────────────────────────────────────────────────────

fn uv_binary_file_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "uv.exe"
    } else {
        "uv"
    }
}

fn first_existing_path(candidates: &[PathBuf]) -> Option<PathBuf> {
    candidates.iter().find(|path| path.is_file()).cloned()
}

fn find_binary_on_path(binary_name: &str) -> Option<PathBuf> {
    let path_var = std::env::var_os("PATH")?;
    std::env::split_paths(&path_var)
        .map(|dir| dir.join(binary_name))
        .find(|candidate| candidate.is_file())
}

fn default_uv_search_paths(home_dir: Option<PathBuf>) -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    let binary_name = uv_binary_file_name();

    #[cfg(target_os = "macos")]
    {
        candidates.push(PathBuf::from("/opt/homebrew/bin").join(binary_name));
        candidates.push(PathBuf::from("/usr/local/bin").join(binary_name));
    }

    #[cfg(target_os = "linux")]
    {
        candidates.push(PathBuf::from("/usr/local/bin").join(binary_name));
        candidates.push(PathBuf::from("/usr/bin").join(binary_name));
    }

    if let Some(home) = home_dir {
        candidates.push(home.join(".cargo").join("bin").join(binary_name));
        candidates.push(home.join(".local").join("bin").join(binary_name));
    }

    #[cfg(target_os = "windows")]
    {
        if let Some(home) = std::env::var_os("USERPROFILE") {
            let home = PathBuf::from(home);
            candidates.push(home.join(".cargo").join("bin").join(binary_name));
        }
        if let Some(local_app_data) = std::env::var_os("LOCALAPPDATA") {
            candidates.push(
                PathBuf::from(local_app_data)
                    .join("Programs")
                    .join("uv")
                    .join(binary_name),
            );
        }
    }

    candidates
}

fn bundled_uv_candidates(resource_dir: &Path) -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    #[cfg(target_os = "windows")]
    let bundled_names = vec![uv_binary_file_name(), "uv"];
    #[cfg(not(target_os = "windows"))]
    let bundled_names = vec![uv_binary_file_name()];
    let bundled_roots = vec!["bundled-tools", "src-tauri/bundled-tools"];

    for candidate_name in bundled_names {
        for bundled_root in &bundled_roots {
            let bundled_relative = format!("{bundled_root}/{candidate_name}");
            candidates.push(resolve_resource_path(
                &resource_dir.to_path_buf(),
                &bundled_relative,
            ));
        }
        candidates.push(
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("bundled-tools")
                .join(candidate_name),
        );
    }

    candidates
}

fn uv_search_candidates(resource_dir: &Path) -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    let binary_name = uv_binary_file_name();

    if let Ok(raw) = std::env::var("INQUIRA_UV_BIN") {
        let trimmed = raw.trim();
        if !trimmed.is_empty() {
            candidates.push(PathBuf::from(trimmed));
        }
    }

    candidates.extend(bundled_uv_candidates(resource_dir));

    if let Some(path_candidate) = find_binary_on_path(binary_name) {
        candidates.push(path_candidate);
    }

    candidates.extend(default_uv_search_paths(dirs_next::home_dir()));
    candidates
}

fn missing_uv_binary_error() -> String {
    format!(
        "Could not find the `{}` binary. Checked bundled desktop resources, {}{}, and common install locations. Install uv, set INQUIRA_UV_BIN to the full binary path, or use `make build-desktop` so src-tauri/bundled-tools/{} is staged for local desktop builds.",
        uv_binary_file_name(),
        "PATH",
        if cfg!(target_os = "macos") {
            " including /opt/homebrew/bin"
        } else {
            ""
        },
        uv_binary_file_name(),
    )
}

fn find_uv_binary(resource_dir: &PathBuf) -> Result<PathBuf, String> {
    if let Some(path) = first_existing_path(&uv_search_candidates(resource_dir)) {
        return Ok(path);
    }

    Err(missing_uv_binary_error())
}

fn backend_env_fingerprint(backend_dir: &PathBuf) -> String {
    let pyproject_path = backend_dir.join("pyproject.toml");
    let lock_path = backend_dir.join("uv.lock");

    let pyproject_content = fs::read_to_string(pyproject_path).unwrap_or_default();
    let lock_content = fs::read_to_string(lock_path).unwrap_or_default();

    let mut hasher = DefaultHasher::new();
    pyproject_content.hash(&mut hasher);
    lock_content.hash(&mut hasher);
    format!("{:x}", hasher.finish())
}

fn needs_python_bootstrap(
    venv_path: &PathBuf,
    marker_path: &PathBuf,
    expected_fingerprint: &str,
    always_sync: bool,
) -> bool {
    if always_sync || !venv_path.exists() {
        return true;
    }

    match fs::read_to_string(marker_path) {
        Ok(existing) => existing.trim() != expected_fingerprint,
        Err(_) => true,
    }
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
        let status = cmd
            .status()
            .map_err(|e| format!("uv python install failed: {}", e))?;
        if !status.success() {
            return Err("uv python install returned non-zero exit code".to_string());
        }
    }

    log::info!("Syncing Python environment...");
    let mut cmd = Command::new(uv_bin);
    cmd.args(["sync", "--project", backend_dir.to_str().unwrap()])
        .env("UV_PROJECT_ENVIRONMENT", venv_path.to_str().unwrap());
    apply_uv_package_env(&mut cmd, config);
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

fn resolve_uv_index_url(config: &InquiraConfig) -> String {
    if let Ok(url) = std::env::var("INQUIRA_UV_INDEX_URL") {
        let trimmed = url.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }

    if let Some(url) = config.python.as_ref().and_then(|p| p.index_url.clone()) {
        let trimmed = url.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }

    "https://pypi.org/simple".to_string()
}

fn apply_uv_package_env(cmd: &mut Command, config: &InquiraConfig) {
    apply_proxy_env(cmd, config);
    cmd.env("UV_INDEX_URL", resolve_uv_index_url(config));
}

fn python_bin_from_venv(venv_path: &PathBuf) -> PathBuf {
    if cfg!(target_os = "windows") {
        venv_path.join("Scripts").join("python.exe")
    } else {
        venv_path.join("bin").join("python")
    }
}

fn parse_lsof_pid_lines(raw: &[u8]) -> Vec<String> {
    let mut pids: Vec<String> = Vec::new();
    for line in String::from_utf8_lossy(raw).lines() {
        let pid = line.trim();
        if pid.is_empty() {
            continue;
        }
        if !pid.chars().all(|ch| ch.is_ascii_digit()) {
            continue;
        }
        if pids.iter().any(|existing| existing == pid) {
            continue;
        }
        pids.push(pid.to_string());
    }
    pids
}

fn list_listening_pids_on_port(port: u16) -> Vec<String> {
    let output = Command::new("lsof")
        .args(["-t", "-nP", "-iTCP"])
        .arg(format!("{port}"))
        .args(["-sTCP:LISTEN"])
        .output();

    let Ok(output) = output else {
        return Vec::new();
    };
    if !output.status.success() {
        return Vec::new();
    }
    parse_lsof_pid_lines(&output.stdout)
}

fn kill_all_listeners_on_port(port: u16) -> usize {
    let pids = list_listening_pids_on_port(port);
    let mut killed = 0usize;
    for pid in pids {
        let status = Command::new("kill").args(["-9", &pid]).status();
        match status {
            Ok(s) if s.success() => {
                log::warn!("Killed process {} listening on port {}", pid, port);
                killed += 1;
            }
            Ok(s) => {
                log::warn!(
                    "Failed to kill process {} on port {} (exit status: {})",
                    pid,
                    port,
                    s
                );
            }
            Err(e) => {
                log::warn!(
                    "Failed to execute kill for pid {} on port {}: {}",
                    pid,
                    port,
                    e
                );
            }
        }
    }
    killed
}

fn ensure_ports_available(
    ports: &[u16],
    app: &tauri::AppHandle,
    phase: &str,
) -> Result<(), String> {
    let mut busy_ports: Vec<(u16, Vec<String>)> = Vec::new();
    for port in ports {
        let pids = list_listening_pids_on_port(*port);
        if !pids.is_empty() {
            busy_ports.push((*port, pids));
        }
    }

    if busy_ports.is_empty() {
        return Ok(());
    }

    let summary = busy_ports
        .iter()
        .map(|(port, pids)| format!("{port} [{}]", pids.join(",")))
        .collect::<Vec<_>>()
        .join(", ");
    let _ = app.emit(
        "backend-status",
        format!("Ports busy during {phase}: {summary}. Cleaning up listeners..."),
    );

    for (port, _) in &busy_ports {
        let _ = kill_all_listeners_on_port(*port);
    }

    for port in ports {
        if !list_listening_pids_on_port(*port).is_empty() {
            let msg = format!("Port {port} is still busy after cleanup.");
            emit_startup_message(app, msg.clone());
            return Err(msg);
        }
    }

    Ok(())
}

fn start_backend(
    uv_bin: &PathBuf,
    backend_dir: &PathBuf,
    venv_path: &PathBuf,
    config: &InquiraConfig,
    inquira_toml_path: &PathBuf,
    shared_secret: &str,
    log_path: &Path,
) -> Result<StdChild, String> {
    let _ = uv_bin; // kept for signature compatibility with existing call sites
    let port = config.backend.as_ref().and_then(|b| b.port).unwrap_or(8000);
    let host = config
        .backend
        .as_ref()
        .and_then(|b| b.host.clone())
        .unwrap_or_else(|| "localhost".to_string());

    log::info!("Starting Inquira backend on port {}...", port);

    let python_bin = python_bin_from_venv(venv_path);
    if !python_bin.exists() {
        return Err(format!(
            "Python executable not found in venv: {}",
            python_bin.display()
        ));
    }

    let mut cmd = Command::new(&python_bin);
    let console_log_level = resolve_shared_console_log_level(config);
    let execution_provider = config
        .execution
        .as_ref()
        .and_then(|e| e.provider.clone())
        .unwrap_or_else(|| "local_jupyter".to_string());

    cmd.args(["-m", "app.main"])
        .current_dir(backend_dir)
        .env("VIRTUAL_ENV", venv_path.to_str().unwrap())
        .env("INQUIRA_HOST", host)
        .env("INQUIRA_PORT", port.to_string())
        .env("INQUIRA_DESKTOP", "1")
        .env("INQUIRA_AGENT_SHARED_SECRET", shared_secret)
        .env(
            "INQUIRA_TOML_PATH",
            inquira_toml_path.to_string_lossy().to_string(),
        )
        .env("INQUIRA_LOG_CONSOLE_LEVEL", console_log_level)
        .env("INQUIRA_EXECUTION_PROVIDER", execution_provider);

    apply_proxy_env(&mut cmd, config);
    redirect_command_output(
        &mut cmd,
        log_path,
        "backend",
        &format!("{} -m app.main", python_bin.display()),
        backend_dir,
    )?;

    let child = cmd
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}. See {}", e, log_path.display()))?;

    Ok(child)
}

fn load_or_create_agent_shared_secret(data_dir: &PathBuf) -> Result<String, String> {
    let secret_path = data_dir.join(".agent-shared-secret");
    if secret_path.exists() {
        let existing = fs::read_to_string(&secret_path)
            .map_err(|e| format!("Failed to read agent secret: {}", e))?;
        let trimmed = existing.trim().to_string();
        if !trimmed.is_empty() {
            return Ok(trimmed);
        }
    }
    let generated = format!("inquira-agent-{}", std::process::id());
    fs::write(&secret_path, &generated)
        .map_err(|e| format!("Failed to write agent secret: {}", e))?;
    Ok(generated)
}

fn start_agent_runtime(
    agent_dir: &PathBuf,
    venv_path: &PathBuf,
    config: &InquiraConfig,
    inquira_toml_path: &PathBuf,
    shared_secret: &str,
    log_path: &Path,
) -> Result<StdChild, String> {
    let python_bin = python_bin_from_venv(venv_path);
    if !python_bin.exists() {
        return Err(format!(
            "Python executable not found in venv: {}",
            python_bin.display()
        ));
    }

    let agent_host = config
        .agent_service
        .as_ref()
        .and_then(|a| a.host.clone())
        .unwrap_or_else(|| "127.0.0.1".to_string());
    let agent_port = config
        .agent_service
        .as_ref()
        .and_then(|a| a.port)
        .unwrap_or(8123);
    let command_override = config
        .agent_service
        .as_ref()
        .and_then(|a| a.command.clone())
        .unwrap_or_default();
    let console_log_level = resolve_shared_console_log_level(config);
    let langgraph_bin = if cfg!(target_os = "windows") {
        venv_path.join("Scripts").join("langgraph.exe")
    } else {
        venv_path.join("bin").join("langgraph")
    };

    let command_summary: String;
    let mut cmd = if command_override.trim().is_empty() {
        if langgraph_bin.exists() {
            let mut c = Command::new(&langgraph_bin);
            c.args([
                "dev",
                "--config",
                "langgraph.json",
                "--host",
                &agent_host,
                "--port",
                &agent_port.to_string(),
                "--no-browser",
                "--no-reload",
            ]);
            command_summary = format!(
                "{} dev --config langgraph.json --host {} --port {} --no-browser --no-reload",
                langgraph_bin.display(),
                agent_host,
                agent_port
            );
            c
        } else {
            let mut c = Command::new(&python_bin);
            c.args([
                "-m",
                "langgraph_cli.cli",
                "dev",
                "--config",
                "langgraph.json",
                "--host",
                &agent_host,
                "--port",
                &agent_port.to_string(),
                "--no-browser",
                "--no-reload",
            ]);
            command_summary = format!(
                "{} -m langgraph_cli.cli dev --config langgraph.json --host {} --port {} --no-browser --no-reload",
                python_bin.display(),
                agent_host,
                agent_port
            );
            c
        }
    } else {
        let mut parts = command_override.split_whitespace();
        let head = parts
            .next()
            .ok_or_else(|| "Invalid agent_service.command".to_string())?;
        let mut c = Command::new(head);
        for part in parts {
            c.arg(part);
        }
        command_summary = command_override.clone();
        c
    };

    cmd.current_dir(agent_dir)
        .env("VIRTUAL_ENV", venv_path.to_string_lossy().to_string())
        .env(
            "INQUIRA_TOML_PATH",
            inquira_toml_path.to_string_lossy().to_string(),
        )
        .env("LOG_LEVEL", console_log_level)
        .env("INQUIRA_AGENT_SHARED_SECRET", shared_secret)
        .env("INQUIRA_AGENT_HOST", agent_host)
        .env("INQUIRA_AGENT_PORT", agent_port.to_string())
        .env("PYTHONPATH", agent_dir.display().to_string());
    apply_proxy_env(&mut cmd, config);
    redirect_command_output(&mut cmd, log_path, "agent", &command_summary, agent_dir)?;

    let child = cmd.spawn().map_err(|e| {
        format!(
            "Failed to start agent runtime: {}. See {}",
            e,
            log_path.display()
        )
    })?;
    Ok(child)
}

fn wait_for_http_health(
    host: &str,
    port: u16,
    path: &str,
    timeout: Duration,
) -> Result<String, String> {
    let start = Instant::now();
    while start.elapsed() < timeout {
        match TcpStream::connect((host, port)) {
            Ok(mut stream) => {
                let req = format!(
                    "GET {} HTTP/1.1\r\nHost: {}:{}\r\nConnection: close\r\n\r\n",
                    path, host, port
                );
                if stream.write_all(req.as_bytes()).is_ok() {
                    let mut body = String::new();
                    let _ = stream.read_to_string(&mut body);
                    if body.starts_with("HTTP/1.1 200") || body.starts_with("HTTP/1.0 200") {
                        return Ok(body);
                    }
                }
            }
            Err(_) => {}
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    Err(format!("Timed out waiting for {}:{}{}", host, port, path))
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
        .manage(AgentProcess(Mutex::new(None)))
        .manage(PtySessions(Mutex::new(HashMap::new())))
        .manage(StartupState(Mutex::new(StartupSnapshot::default())))
        .setup(|app| {
            // Set up logging in debug mode
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            update_startup_state(
                &app.handle(),
                false,
                "",
                "Launching desktop services...",
            );
            show_main_window(&app.handle());

            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                let startup_result: Result<(), String> = (|| {
                    let resource_dir = app_handle
                        .path()
                        .resource_dir()
                        .unwrap_or_else(|_| PathBuf::from("."));
                    let data_dir = app_handle.path().app_data_dir().unwrap_or_else(|_| {
                        dirs_next::home_dir()
                            .unwrap_or_else(|| PathBuf::from("."))
                            .join(".inquira")
                    });
                    fs::create_dir_all(&data_dir).ok();
                    let log_paths = startup_log_paths(&data_dir);
                    append_startup_log(
                        &log_paths.desktop,
                        &format!("Desktop startup begin. data_dir={}", data_dir.display()),
                    );

                    let uv_bin = find_uv_binary(&resource_dir)
                        .map_err(|error| format!("Startup failed: {error}"))?;
                    let backend_dir = if cfg!(debug_assertions) {
                        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend")
                    } else {
                        resolve_resource_path(&resource_dir, "backend")
                    };
                    let config_path = resolve_resource_path(&resource_dir, "inquira.toml");
                    let runtime_config_path = if config_path.exists() {
                        config_path.clone()
                    } else {
                        backend_dir
                            .parent()
                            .unwrap_or(&backend_dir)
                            .join("inquira.toml")
                    };
                    let config = load_config(&runtime_config_path);
                    ensure_windows_vc_redist(&data_dir, &log_paths.desktop, &config, &app_handle)
                        .map_err(|error| format!("Startup failed: {error}"))?;
                    let managed_ports = vec![8000_u16, 8123_u16];
                    log::info!(
                        "Runtime config path: {}",
                        runtime_config_path.to_string_lossy()
                    );
                    log::info!(
                        "Configured execution provider: {}",
                        config
                            .execution
                            .as_ref()
                            .and_then(|e| e.provider.clone())
                            .unwrap_or_else(|| "local_jupyter".to_string())
                    );
                    let agent_dir = if cfg!(debug_assertions) {
                        let configured = config
                            .agent_service
                            .as_ref()
                            .and_then(|a| a.path.clone())
                            .unwrap_or_else(|| "../agents".to_string());
                        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(configured)
                    } else {
                        resolve_resource_path(&resource_dir, "agents")
                    };
                    let venv_path = data_dir.join(".venv");
                    let backend_env_marker = data_dir.join(".backend-env-fingerprint");
                    let expected_backend_env_fingerprint = backend_env_fingerprint(&backend_dir);
                    let always_sync_backend_env = cfg!(debug_assertions);
                    let should_bootstrap_python = needs_python_bootstrap(
                        &venv_path,
                        &backend_env_marker,
                        &expected_backend_env_fingerprint,
                        always_sync_backend_env,
                    );
                    if should_bootstrap_python {
                        if always_sync_backend_env {
                            log::info!("Debug mode: syncing backend Python environment...");
                        } else {
                            log::info!(
                                "Backend dependencies changed. Re-syncing Python environment..."
                            );
                        }
                        emit_startup_message(
                            &app_handle,
                            "Installing Python environment (one-time setup)...",
                        );

                        bootstrap_python(&uv_bin, &backend_dir, &venv_path, &config)
                            .map_err(|error| format!("Setup failed: {error}"))?;

                        if let Err(error) =
                            fs::write(&backend_env_marker, &expected_backend_env_fingerprint)
                        {
                            log::warn!("Could not write backend env marker: {}", error);
                        }
                    }

                    let shared_secret = load_or_create_agent_shared_secret(&data_dir)
                        .map_err(|error| format!("Startup failed: {error}"))?;

                    ensure_ports_available(&managed_ports, &app_handle, "startup preflight")
                        .map_err(|error| format!("Startup failed: {error}"))?;

                    emit_startup_message(&app_handle, "Starting agent service...");
                    append_startup_log(
                        &log_paths.desktop,
                        &format!("Starting agent runtime. log={}", log_paths.agent.display()),
                    );
                    match start_agent_runtime(
                        &agent_dir,
                        &venv_path,
                        &config,
                        &runtime_config_path,
                        &shared_secret,
                        &log_paths.agent,
                    ) {
                        Ok(child) => {
                            log::info!("Agent runtime started (PID: {})", child.id());
                            let state = app_handle.state::<AgentProcess>();
                            *state.0.lock().unwrap() = Some(child);
                        }
                        Err(error) => {
                            for port in &managed_ports {
                                let _ = kill_all_listeners_on_port(*port);
                            }
                            return Err(format!("Agent failed: {error}"));
                        }
                    }

                    emit_startup_message(&app_handle, "Starting backend service...");
                    append_startup_log(
                        &log_paths.desktop,
                        &format!("Starting backend. log={}", log_paths.backend.display()),
                    );
                    match start_backend(
                        &uv_bin,
                        &backend_dir,
                        &venv_path,
                        &config,
                        &runtime_config_path,
                        &shared_secret,
                        &log_paths.backend,
                    ) {
                        Ok(child) => {
                            log::info!("Backend process started (PID: {})", child.id());
                            let state = app_handle.state::<BackendProcess>();
                            *state.0.lock().unwrap() = Some(child);
                        }
                        Err(error) => {
                            stop_agent_process(&app_handle);
                            for port in &managed_ports {
                                let _ = kill_all_listeners_on_port(*port);
                            }
                            return Err(format!("Backend failed: {error}"));
                        }
                    }

                    emit_startup_message(&app_handle, "Checking service health...");
                    let backend_host = config
                        .backend
                        .as_ref()
                        .and_then(|b| b.host.clone())
                        .unwrap_or_else(|| "localhost".to_string());
                    let backend_port = config.backend.as_ref().and_then(|b| b.port).unwrap_or(8000);
                    let agent_host = config
                        .agent_service
                        .as_ref()
                        .and_then(|a| a.host.clone())
                        .unwrap_or_else(|| "127.0.0.1".to_string());
                    let agent_port = config
                        .agent_service
                        .as_ref()
                        .and_then(|a| a.port)
                        .unwrap_or(8123);
                    let timeout_sec = config
                        .agent_service
                        .as_ref()
                        .and_then(|a| a.startup_timeout_sec)
                        .unwrap_or(45);

                    wait_for_http_health(
                        &backend_host,
                        backend_port,
                        "/health",
                        Duration::from_secs(timeout_sec),
                    )
                    .map_err(|error| {
                        stop_backend_process(&app_handle);
                        stop_agent_process(&app_handle);
                        for port in &managed_ports {
                            let _ = kill_all_listeners_on_port(*port);
                        }
                        format!("Backend health failed: {error}")
                    })?;

                    wait_for_http_health(
                        &agent_host,
                        agent_port,
                        "/ok",
                        Duration::from_secs(timeout_sec),
                    )
                    .map_err(|error| {
                        stop_backend_process(&app_handle);
                        stop_agent_process(&app_handle);
                        for port in &managed_ports {
                            let _ = kill_all_listeners_on_port(*port);
                        }
                        format!("Agent health failed: {error}")
                    })?;

                    let _ = app_handle.emit("backend-status", "ready");
                    append_startup_log(&log_paths.desktop, "Desktop startup ready.");
                    Ok(())
                })();

                match startup_result {
                    Ok(()) => update_startup_state(&app_handle, true, "", ""),
                    Err(error) => {
                        log::error!("Desktop startup failed: {}", error);
                        let data_dir = app_handle.path().app_data_dir().unwrap_or_else(|_| {
                            dirs_next::home_dir()
                                .unwrap_or_else(|| PathBuf::from("."))
                                .join(".inquira")
                        });
                        let log_paths = startup_log_paths(&data_dir);
                        append_startup_log(
                            &log_paths.desktop,
                            &format!("Desktop startup failed: {}", error),
                        );
                        update_startup_state(
                            &app_handle,
                            false,
                            format!(
                                "{} Desktop log: {} Backend log: {} Agent log: {}",
                                error,
                                log_paths.desktop.display(),
                                log_paths.backend.display(),
                                log_paths.agent.display()
                            ),
                            "",
                        );
                    }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
            get_startup_state,
            auth_start_loopback_listener,
            open_external_url,
            tauri_terminal_start,
            tauri_terminal_write,
            tauri_terminal_resize,
            tauri_terminal_stop
        ])
        .build(tauri::generate_context!())
        .expect("error while building Inquira")
        .run(|app, event| {
            let should_shutdown_children = matches!(
                event,
                tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
            );
            if !should_shutdown_children {
                return;
            }

            stop_agent_process(app);
            stop_backend_process(app);
            let _ = kill_all_listeners_on_port(8000);
            let _ = kill_all_listeners_on_port(8123);

            if let Some(sessions) = app.try_state::<PtySessions>() {
                if let Ok(mut guard) = sessions.0.lock() {
                    for (session_id, mut session) in guard.drain() {
                        let _ = session.child.kill();
                        let _ = app.emit("terminal:pty-exit", PtyExitEvent { session_id });
                    }
                }
            }
        });
}

#[cfg(test)]
mod tests {
    use super::{
        bundled_uv_candidates, default_uv_search_paths, detect_default_shell,
        missing_uv_binary_error, needs_python_bootstrap, parse_lsof_pid_lines, resolve_pty_cwd,
        resolve_resource_path, resolve_shared_console_log_level, resolve_uv_index_url,
        startup_log_paths, stop_child_process, uv_binary_file_name, uv_search_candidates,
        vc_redist_download_url, vc_redist_installer_path, vc_redist_marker_path,
        vc_redist_success_exit_code, InquiraConfig, LoggingConfig, PythonConfig,
    };
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::process::Command;

    #[test]
    fn bootstrap_required_when_venv_missing() {
        let venv = PathBuf::from("/tmp/inq-missing-venv");
        let marker = PathBuf::from("/tmp/inq-missing-marker");
        assert!(needs_python_bootstrap(&venv, &marker, "abc", false));
    }

    #[test]
    fn bootstrap_required_when_fingerprint_mismatch() {
        let base = std::env::temp_dir().join("inq_bootstrap_test_mismatch");
        let _ = fs::create_dir_all(&base);
        let venv = base.join(".venv");
        let marker = base.join(".backend-env-fingerprint");
        let _ = fs::create_dir_all(&venv);
        fs::write(&marker, "old").expect("write marker");

        assert!(needs_python_bootstrap(&venv, &marker, "new", false));
    }

    #[test]
    fn bootstrap_not_required_when_fingerprint_matches() {
        let base = std::env::temp_dir().join("inq_bootstrap_test_match");
        let _ = fs::create_dir_all(&base);
        let venv = base.join(".venv");
        let marker = base.join(".backend-env-fingerprint");
        let _ = fs::create_dir_all(&venv);
        fs::write(&marker, "same").expect("write marker");

        assert!(!needs_python_bootstrap(&venv, &marker, "same", false));
    }

    #[test]
    fn stop_child_process_terminates_running_child() {
        let mut child = if cfg!(target_os = "windows") {
            Command::new("cmd")
                .args(["/C", "timeout /T 30 /NOBREAK >NUL"])
                .spawn()
                .expect("spawn child")
        } else {
            Command::new("sh")
                .args(["-c", "sleep 30"])
                .spawn()
                .expect("spawn child")
        };

        stop_child_process("test", &mut child);
        let status = child.try_wait().expect("query child status");
        assert!(status.is_some(), "child should be terminated");
    }

    #[test]
    fn parse_lsof_pid_lines_keeps_numeric_unique_pids() {
        let raw = b"1234\n\nabc\n1234\n5678\n";
        let parsed = parse_lsof_pid_lines(raw);
        assert_eq!(parsed, vec!["1234".to_string(), "5678".to_string()]);
    }

    #[test]
    fn startup_log_paths_use_logs_subdirectory() {
        let base = PathBuf::from("/tmp/inquira-app-data");
        let paths = startup_log_paths(&base);

        assert_eq!(paths.desktop, base.join("logs").join("desktop-startup.log"));
        assert_eq!(paths.backend, base.join("logs").join("backend-startup.log"));
        assert_eq!(paths.agent, base.join("logs").join("agent-startup.log"));
    }

    #[test]
    fn vc_redist_paths_live_under_app_data() {
        let base = PathBuf::from("/tmp/inquira-app-data");

        assert_eq!(
            vc_redist_marker_path(&base),
            base.join(".vc_redist_installed")
        );
        assert_eq!(
            vc_redist_installer_path(&base),
            base.join("bootstrap").join("vc_redist.x64.exe")
        );
    }

    #[test]
    fn vc_redist_download_url_uses_microsoft_permalink() {
        assert_eq!(
            vc_redist_download_url(),
            "https://aka.ms/vc14/vc_redist.x64.exe"
        );
    }

    #[test]
    fn vc_redist_success_exit_code_accepts_known_success_variants() {
        assert!(vc_redist_success_exit_code(0));
        assert!(vc_redist_success_exit_code(1638));
        assert!(vc_redist_success_exit_code(3010));
        assert!(!vc_redist_success_exit_code(1));
    }

    fn base_config_with_index(index_url: Option<&str>) -> InquiraConfig {
        InquiraConfig {
            python: Some(PythonConfig {
                version: None,
                index_url: index_url.map(|s| s.to_string()),
                python_path: None,
            }),
            proxy: None,
            backend: None,
            execution: None,
            agent_service: None,
            logging: None,
        }
    }

    #[test]
    fn uv_index_url_defaults_to_pypi_when_not_configured() {
        std::env::remove_var("INQUIRA_UV_INDEX_URL");
        let config = InquiraConfig {
            python: None,
            proxy: None,
            backend: None,
            execution: None,
            agent_service: None,
            logging: None,
        };
        assert_eq!(resolve_uv_index_url(&config), "https://pypi.org/simple");
    }

    #[test]
    fn shared_console_log_level_defaults_to_error() {
        std::env::remove_var("INQUIRA_LOG_CONSOLE_LEVEL");
        let config = InquiraConfig {
            python: None,
            proxy: None,
            backend: None,
            execution: None,
            agent_service: None,
            logging: None,
        };
        assert_eq!(resolve_shared_console_log_level(&config), "ERROR");
    }

    #[test]
    fn shared_console_log_level_uses_toml_and_env_override() {
        std::env::remove_var("INQUIRA_LOG_CONSOLE_LEVEL");
        let config = InquiraConfig {
            python: None,
            proxy: None,
            backend: None,
            execution: None,
            agent_service: None,
            logging: Some(LoggingConfig {
                console_level: Some("info".to_string()),
            }),
        };
        assert_eq!(resolve_shared_console_log_level(&config), "INFO");

        std::env::set_var("INQUIRA_LOG_CONSOLE_LEVEL", "critical");
        assert_eq!(resolve_shared_console_log_level(&config), "CRITICAL");
        std::env::remove_var("INQUIRA_LOG_CONSOLE_LEVEL");
    }

    #[test]
    fn uv_index_url_uses_toml_when_env_missing() {
        std::env::remove_var("INQUIRA_UV_INDEX_URL");
        let config = base_config_with_index(Some("https://company.example/simple"));
        assert_eq!(
            resolve_uv_index_url(&config),
            "https://company.example/simple"
        );
    }

    #[test]
    fn uv_index_url_env_overrides_toml() {
        let config = base_config_with_index(Some("https://company.example/simple"));
        std::env::set_var("INQUIRA_UV_INDEX_URL", "https://override.example/simple");
        assert_eq!(
            resolve_uv_index_url(&config),
            "https://override.example/simple"
        );
        std::env::remove_var("INQUIRA_UV_INDEX_URL");
    }

    #[test]
    fn resolve_resource_path_prefers_direct_resource() {
        let base = std::env::temp_dir().join("inq_resource_path_direct");
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(base.join("backend")).expect("create backend dir");

        let resolved = resolve_resource_path(&base, "backend");
        assert_eq!(resolved, base.join("backend"));
    }

    #[test]
    fn resolve_resource_path_falls_back_to_up_directory() {
        let base = std::env::temp_dir().join("inq_resource_path_up");
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(base.join("_up_").join("backend")).expect("create _up_/backend dir");

        let resolved = resolve_resource_path(&base, "backend");
        assert_eq!(resolved, base.join("_up_").join("backend"));
    }

    #[test]
    fn uv_search_candidates_include_env_override_and_manifest_bundle() {
        let base = std::env::temp_dir().join("inq_uv_candidates");
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(&base).expect("create resource dir");

        let override_path = base.join("custom").join(uv_binary_file_name());
        std::env::set_var(
            "INQUIRA_UV_BIN",
            override_path.to_string_lossy().to_string(),
        );

        let candidates = uv_search_candidates(&base);

        assert_eq!(candidates.first(), Some(&override_path));
        assert!(
            candidates
                .iter()
                .any(|path| path.ends_with(Path::new("bundled-tools").join(uv_binary_file_name()))),
            "expected manifest bundled-tools fallback in uv search candidates"
        );

        std::env::remove_var("INQUIRA_UV_BIN");
    }

    #[test]
    fn bundled_uv_candidates_include_windows_fallback_name() {
        let base = std::env::temp_dir().join("inq_uv_bundle_candidates");
        let _ = fs::remove_dir_all(&base);
        fs::create_dir_all(&base).expect("create resource dir");

        let candidates = bundled_uv_candidates(&base);

        assert!(
            candidates
                .iter()
                .any(|path| path.ends_with(Path::new("bundled-tools").join(uv_binary_file_name()))),
            "expected bundled candidates to include the platform uv binary name"
        );
        assert!(
            candidates.iter().any(|path| {
                path.ends_with(
                    Path::new("src-tauri")
                        .join("bundled-tools")
                        .join(uv_binary_file_name()),
                )
            }),
            "expected bundled candidates to include the legacy src-tauri resource layout"
        );

        #[cfg(target_os = "windows")]
        assert!(
            candidates
                .iter()
                .any(|path| path.ends_with(Path::new("bundled-tools").join("uv"))),
            "expected bundled candidates to include a plain `uv` fallback on Windows"
        );
    }

    #[test]
    fn uv_search_common_paths_include_home_cargo_bin() {
        let home = std::env::temp_dir().join("inq_uv_home");
        let candidates = default_uv_search_paths(Some(home.clone()));
        assert!(
            candidates
                .iter()
                .any(|path| path == &home.join(".cargo").join("bin").join(uv_binary_file_name())),
            "expected home cargo bin fallback in uv search paths"
        );
    }

    #[test]
    fn missing_uv_binary_error_is_actionable() {
        let error = missing_uv_binary_error();
        assert!(error.contains("Could not find the"));
        assert!(error.contains("INQUIRA_UV_BIN"));
        assert!(error.contains("make build-desktop"));
    }

    #[test]
    fn detect_default_shell_is_non_empty_across_platforms() {
        let (shell, _args) = detect_default_shell();
        assert!(!shell.trim().is_empty());
    }

    #[test]
    fn resolve_pty_cwd_uses_existing_directory() {
        let dir = std::env::temp_dir();
        let resolved = resolve_pty_cwd(Some(dir.to_string_lossy().to_string()));
        assert_eq!(resolved, dir.to_string_lossy().to_string());
    }
}
