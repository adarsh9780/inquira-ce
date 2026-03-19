use std::collections::HashMap;
use std::fs;
use std::hash::{DefaultHasher, Hash, Hasher};
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child as StdChild, Command};
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
                            log::warn!(
                                "Failed while waiting for graceful {name} shutdown: {e}"
                            );
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

fn find_uv_binary(resource_dir: &PathBuf) -> PathBuf {
    // In production, UV is bundled in resources/
    let bundled_unix = resolve_resource_path(resource_dir, "bundled-tools/uv");
    if bundled_unix.exists() {
        return bundled_unix;
    }
    let bundled_windows = resolve_resource_path(resource_dir, "bundled-tools/uv.exe");
    if bundled_windows.exists() {
        return bundled_windows;
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
                log::warn!("Failed to execute kill for pid {} on port {}: {}", pid, port, e);
            }
        }
    }
    killed
}

fn ensure_ports_available(ports: &[u16], app: &tauri::AppHandle, phase: &str) -> Result<(), String> {
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
            let _ = app.emit("backend-status", msg.clone());
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
) -> Result<StdChild, String> {
    let _ = uv_bin; // kept for signature compatibility with existing call sites
    let port = config.backend.as_ref().and_then(|b| b.port).unwrap_or(8000);

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
        .env("INQUIRA_PORT", port.to_string())
        .env("INQUIRA_DESKTOP", "1")
        .env(
            "INQUIRA_TOML_PATH",
            inquira_toml_path.to_string_lossy().to_string(),
        )
        .env("INQUIRA_LOG_CONSOLE_LEVEL", console_log_level)
        .env("INQUIRA_EXECUTION_PROVIDER", execution_provider);

    apply_proxy_env(&mut cmd, config);

    let child = cmd
        .spawn()
        .map_err(|e| format!("Failed to start backend: {}", e))?;

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
        c
    };

    cmd.current_dir(agent_dir)
        .env("VIRTUAL_ENV", venv_path.to_string_lossy().to_string())
        .env("INQUIRA_TOML_PATH", inquira_toml_path.to_string_lossy().to_string())
        .env("LOG_LEVEL", console_log_level)
        .env("INQUIRA_AGENT_SHARED_SECRET", shared_secret)
        .env("INQUIRA_AGENT_HOST", agent_host)
        .env("INQUIRA_AGENT_PORT", agent_port.to_string())
        .env("PYTHONPATH", agent_dir.display().to_string());
    apply_proxy_env(&mut cmd, config);

    let child = cmd
        .spawn()
        .map_err(|e| format!("Failed to start agent runtime: {}", e))?;
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

            let uv_bin = find_uv_binary(&resource_dir);
            // In dev, backend is a sibling directory; in prod, it's bundled in resources
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
            // Phase 1: Bootstrap Python + venv (one-time)
            if should_bootstrap_python {
                if always_sync_backend_env {
                    log::info!("Debug mode: syncing backend Python environment...");
                } else {
                    log::info!("Backend dependencies changed. Re-syncing Python environment...");
                }
                app.emit(
                    "backend-status",
                    "Installing Python environment (one-time setup)...",
                )
                .ok();

                if let Err(e) = bootstrap_python(&uv_bin, &backend_dir, &venv_path, &config) {
                    log::error!("Python bootstrap failed: {}", e);
                    app.emit("backend-status", &format!("Setup failed: {}", e))
                        .ok();
                    // Don't crash — let the user see the error in the UI
                    return Ok(());
                }

                if let Err(e) = fs::write(&backend_env_marker, &expected_backend_env_fingerprint) {
                    log::warn!("Could not write backend env marker: {}", e);
                }
            }

            let shared_secret = match load_or_create_agent_shared_secret(&data_dir) {
                Ok(secret) => secret,
                Err(e) => {
                    app.emit("backend-status", &format!("Startup failed: {}", e))
                        .ok();
                    return Ok(());
                }
            };

            if let Err(e) = ensure_ports_available(&managed_ports, &app.handle(), "startup preflight")
            {
                log::error!("Port preflight failed: {}", e);
                let _ = app.emit("backend-status", format!("Startup failed: {}", e));
                return Ok(());
            }

            app.emit("backend-status", "agent-starting").ok();
            match start_agent_runtime(
                &agent_dir,
                &venv_path,
                &config,
                &runtime_config_path,
                &shared_secret,
            ) {
                Ok(child) => {
                    log::info!("Agent runtime started (PID: {})", child.id());
                    let state = app.state::<AgentProcess>();
                    *state.0.lock().unwrap() = Some(child);
                }
                Err(e) => {
                    log::error!("Agent runtime start failed: {}", e);
                    for port in &managed_ports {
                        let _ = kill_all_listeners_on_port(*port);
                    }
                    app.emit("backend-status", &format!("Agent failed: {}", e))
                        .ok();
                    return Ok(());
                }
            }

            app.emit("backend-status", "backend-starting").ok();
            match start_backend(
                &uv_bin,
                &backend_dir,
                &venv_path,
                &config,
                &runtime_config_path,
            ) {
                Ok(child) => {
                    log::info!("Backend process started (PID: {})", child.id());
                    let state = app.state::<BackendProcess>();
                    *state.0.lock().unwrap() = Some(child);
                }
                Err(e) => {
                    log::error!("Backend start failed: {}", e);
                    stop_agent_process(&app.handle());
                    for port in &managed_ports {
                        let _ = kill_all_listeners_on_port(*port);
                    }
                    app.emit("backend-status", &format!("Backend failed: {}", e))
                        .ok();
                    return Ok(());
                }
            }

            app.emit("backend-status", "health-checking").ok();
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

            let backend_health = wait_for_http_health(
                &backend_host,
                backend_port,
                "/health",
                Duration::from_secs(timeout_sec),
            );
            if let Err(e) = backend_health {
                stop_backend_process(&app.handle());
                stop_agent_process(&app.handle());
                for port in &managed_ports {
                    let _ = kill_all_listeners_on_port(*port);
                }
                app.emit("backend-status", &format!("Backend health failed: {}", e))
                    .ok();
                return Ok(());
            }
            let agent_health = wait_for_http_health(
                &agent_host,
                agent_port,
                "/ok",
                Duration::from_secs(timeout_sec),
            );
            match agent_health {
                Ok(_body) => {}
                Err(e) => {
                    stop_backend_process(&app.handle());
                    stop_agent_process(&app.handle());
                    for port in &managed_ports {
                        let _ = kill_all_listeners_on_port(*port);
                    }
                    app.emit("backend-status", &format!("Agent health failed: {}", e))
                        .ok();
                    return Ok(());
                }
            }

            app.emit("backend-status", "ready").ok();

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_url,
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
        detect_default_shell, needs_python_bootstrap, parse_lsof_pid_lines, resolve_pty_cwd,
        resolve_resource_path, resolve_shared_console_log_level, resolve_uv_index_url,
        stop_child_process, InquiraConfig, LoggingConfig, PythonConfig,
    };
    use std::fs;
    use std::path::PathBuf;
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
