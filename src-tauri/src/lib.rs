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
    execution: Option<ExecutionConfig>,
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
    runner: Option<RunnerConfig>,
}

#[derive(Deserialize, Debug, Clone)]
struct RunnerConfig {
    #[serde(rename = "venv-name")]
    venv_name: Option<String>,
    #[serde(rename = "project-path")]
    project_path: Option<String>,
    #[serde(rename = "safe-py-runner-source")]
    safe_py_runner_source: Option<String>,
    #[serde(rename = "safe-py-runner-pypi")]
    safe_py_runner_pypi: Option<String>,
    #[serde(rename = "safe-py-runner-github")]
    safe_py_runner_github: Option<String>,
    #[serde(rename = "safe-py-runner-local-path")]
    safe_py_runner_local_path: Option<String>,
    packages: Option<Vec<String>>,
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
                }
            }
        }
    } else {
        InquiraConfig {
            python: None,
            proxy: None,
            backend: None,
            execution: None,
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

fn bootstrap_runner_env(
    uv_bin: &PathBuf,
    runner_venv_path: &PathBuf,
    config: &InquiraConfig,
) -> Result<(), String> {
    let python_spec = config
        .python
        .as_ref()
        .and_then(|p| p.python_path.clone())
        .or_else(|| config.python.as_ref().and_then(|p| p.version.clone()))
        .unwrap_or_else(|| "3.12".to_string());

    let runner_python = python_bin_from_venv(runner_venv_path);
    let marker_file = runner_venv_path.join(".inquira_runner_bootstrapped");
    let desired_runner_state = build_runner_state_marker(config);
    let mut needs_package_install = false;
    if !runner_python.exists() {
        log::info!(
            "Creating isolated execution runner venv at {}...",
            runner_venv_path.display()
        );
        let mut cmd = Command::new(uv_bin);
        cmd.arg("venv")
            .arg(runner_venv_path.to_str().unwrap())
            .args(["--python", &python_spec]);
        apply_proxy_env(&mut cmd, config);
        let status = cmd.status().map_err(|e| format!("uv venv failed: {}", e))?;
        if !status.success() {
            return Err("uv venv returned non-zero exit code".to_string());
        }
        needs_package_install = true;
    }

    match fs::read_to_string(&marker_file) {
        Ok(existing) => {
            if existing != desired_runner_state {
                needs_package_install = true;
            }
        }
        Err(_) => {
            needs_package_install = true;
        }
    }

    if !needs_package_install {
        return Ok(());
    }

    let mut packages = vec![
        "narwhals".to_string(),
        "duckdb".to_string(),
        "pandas".to_string(),
        "plotly".to_string(),
    ];

    if let Some(exec) = &config.execution {
        if let Some(runner) = &exec.runner {
            if let Some(custom) = &runner.packages {
                if !custom.is_empty() {
                    packages = custom
                        .iter()
                        .filter(|pkg| pkg.as_str() != "safe-py-runner")
                        .cloned()
                        .collect();
                }
            }
        }
    }

    let mut cmd = Command::new(uv_bin);
    cmd.args(["pip", "install", "--python", runner_python.to_str().unwrap()]);

    for pkg in packages {
        cmd.arg(pkg);
    }

    apply_proxy_env(&mut cmd, config);
    let status = cmd
        .status()
        .map_err(|e| format!("runner package install failed: {}", e))?;
    if !status.success() {
        return Err("runner package install returned non-zero exit code".to_string());
    }

    install_safe_py_runner(uv_bin, &runner_python, config)?;

    let _ = fs::write(&marker_file, desired_runner_state);

    Ok(())
}

fn build_runner_state_marker(config: &InquiraConfig) -> String {
    let mut source = "auto".to_string();
    let mut pypi_pkg = "safe-py-runner".to_string();
    let mut github_ref = "git+https://github.com/adarsh9780/safe-py-runner.git".to_string();
    let mut local_path = String::new();
    let mut packages = vec![
        "narwhals".to_string(),
        "duckdb".to_string(),
        "pandas".to_string(),
        "plotly".to_string(),
    ];

    if let Some(exec) = &config.execution {
        if let Some(runner) = &exec.runner {
            if let Some(val) = &runner.safe_py_runner_source {
                source = val.to_lowercase();
            }
            if let Some(val) = &runner.safe_py_runner_pypi {
                pypi_pkg = val.to_string();
            }
            if let Some(val) = &runner.safe_py_runner_github {
                github_ref = val.to_string();
            }
            if let Some(val) = &runner.safe_py_runner_local_path {
                local_path = val.to_string();
            } else if let Some(val) = &runner.project_path {
                local_path = val.to_string();
            }
            if let Some(custom) = &runner.packages {
                if !custom.is_empty() {
                    packages = custom
                        .iter()
                        .filter(|pkg| pkg.as_str() != "safe-py-runner")
                        .cloned()
                        .collect();
                }
            }
        }
    }

    packages.sort();
    format!(
        "source={source}\npypi={pypi_pkg}\ngithub={github_ref}\nlocal={local_path}\npackages={}",
        packages.join(",")
    )
}

fn install_safe_py_runner(
    uv_bin: &PathBuf,
    runner_python: &PathBuf,
    config: &InquiraConfig,
) -> Result<(), String> {
    let mut source = "auto".to_string();
    let mut pypi_pkg = "safe-py-runner".to_string();
    let mut github_ref = "git+https://github.com/adarsh9780/safe-py-runner.git".to_string();
    let mut local_path = None::<String>;

    if let Some(exec) = &config.execution {
        if let Some(runner) = &exec.runner {
            if let Some(val) = &runner.safe_py_runner_source {
                source = val.to_lowercase();
            }
            if let Some(val) = &runner.safe_py_runner_pypi {
                pypi_pkg = val.to_string();
            }
            if let Some(val) = &runner.safe_py_runner_github {
                github_ref = val.to_string();
            }
            if let Some(val) = &runner.safe_py_runner_local_path {
                local_path = Some(val.to_string());
            } else if let Some(val) = &runner.project_path {
                // Backward compatibility with existing config
                local_path = Some(val.to_string());
            }
        }
    }

    let mut attempts: Vec<(String, Vec<String>)> = Vec::new();
    match source.as_str() {
        "pypi" => {
            attempts.push(("PyPI".to_string(), vec![pypi_pkg]));
        }
        "github" => {
            attempts.push(("GitHub".to_string(), vec![github_ref]));
        }
        "local" => {
            if let Some(path) = local_path.clone() {
                attempts.push(("local".to_string(), vec!["-e".to_string(), path]));
            }
        }
        _ => {
            // auto: PyPI -> GitHub -> local (final fallback)
            attempts.push(("PyPI".to_string(), vec![pypi_pkg]));
            attempts.push(("GitHub".to_string(), vec![github_ref]));
            if let Some(path) = local_path.clone() {
                attempts.push(("local".to_string(), vec!["-e".to_string(), path]));
            }
        }
    }

    if attempts.is_empty() {
        return Err(
            "No valid safe-py-runner source configured. Provide local path or select pypi/github."
                .to_string(),
        );
    }

    for (label, args) in attempts {
        if label == "local" && args.len() == 2 {
            let local = PathBuf::from(&args[1]);
            if !local.exists() {
                log::warn!(
                    "safe-py-runner local path does not exist, skipping: {}",
                    local.display()
                );
                continue;
            }
        }

        let mut cmd = Command::new(uv_bin);
        cmd.args(["pip", "install", "--python", runner_python.to_str().unwrap()]);
        for arg in args {
            cmd.arg(arg);
        }
        apply_proxy_env(&mut cmd, config);
        let status = cmd
            .status()
            .map_err(|e| format!("safe-py-runner install command failed: {}", e))?;

        if status.success() {
            log::info!("Installed safe-py-runner from {}", label);
            return Ok(());
        }
        log::warn!("safe-py-runner install from {} failed, trying next source", label);
    }

    Err("Failed to install safe-py-runner from all configured sources".to_string())
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

fn python_bin_from_venv(venv_path: &PathBuf) -> PathBuf {
    if cfg!(target_os = "windows") {
        venv_path.join("Scripts").join("python.exe")
    } else {
        venv_path.join("bin").join("python")
    }
}

fn kill_stale_backend_on_port(port: u16) {
    // Best-effort cleanup for orphan listeners from previous dev runs.
    // We only kill processes whose command includes "app.main".
    let output = Command::new("lsof")
        .args(["-t", "-nP", "-iTCP"])
        .arg(format!("{port}"))
        .args(["-sTCP:LISTEN"])
        .output();

    let Ok(output) = output else {
        return;
    };
    if !output.status.success() {
        return;
    }

    let pids = String::from_utf8_lossy(&output.stdout);
    for pid in pids.lines().map(str::trim).filter(|s| !s.is_empty()) {
        let ps_output = Command::new("ps")
            .args(["-o", "command=", "-p", pid])
            .output();

        let Ok(ps_output) = ps_output else {
            continue;
        };
        if !ps_output.status.success() {
            continue;
        }

        let cmdline = String::from_utf8_lossy(&ps_output.stdout).to_string();
        if cmdline.contains("app.main") {
            log::warn!("Killing stale backend process on port {} (pid {})", port, pid);
            let _ = Command::new("kill").args(["-9", pid]).status();
        }
    }
}

fn start_backend(
    uv_bin: &PathBuf,
    backend_dir: &PathBuf,
    venv_path: &PathBuf,
    runner_python: Option<&PathBuf>,
    config: &InquiraConfig,
    inquira_toml_path: &PathBuf,
) -> Result<Child, String> {
    let _ = uv_bin; // kept for signature compatibility with existing call sites
    let port = config
        .backend
        .as_ref()
        .and_then(|b| b.port)
        .unwrap_or(8000);

    kill_stale_backend_on_port(port);

    log::info!("Starting Inquira backend on port {}...", port);

    let python_bin = python_bin_from_venv(venv_path);
    if !python_bin.exists() {
        return Err(format!(
            "Python executable not found in venv: {}",
            python_bin.display()
        ));
    }

    let mut cmd = Command::new(&python_bin);
    let execution_provider = config
        .execution
        .as_ref()
        .and_then(|e| e.provider.clone())
        .unwrap_or_else(|| "local_subprocess".to_string());

    cmd.args(["-m", "app.main"])
        .current_dir(backend_dir)
        .env("VIRTUAL_ENV", venv_path.to_str().unwrap())
        .env("INQUIRA_PORT", port.to_string())
        .env("INQUIRA_DESKTOP", "1")
        .env("INQUIRA_TOML_PATH", inquira_toml_path.to_string_lossy().to_string())
        .env("INQUIRA_EXECUTION_PROVIDER", execution_provider);

    if let Some(exec) = &config.execution {
        if let Some(runner) = &exec.runner {
            if let Some(path) = &runner.project_path {
                cmd.env("INQUIRA_SAFE_PY_RUNNER_PROJECT_PATH", path);
            }
        }
    }
    if let Some(py) = runner_python {
        cmd.env("INQUIRA_RUNNER_PYTHON", py.to_string_lossy().to_string());
    }

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

            let uv_bin = find_uv_binary(&resource_dir);
            // In dev, backend is a sibling directory; in prod, it's bundled in resources
            let backend_dir = if cfg!(debug_assertions) {
                PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend")
            } else {
                resource_dir.join("backend")
            };
            let config_path = resource_dir.join("inquira.toml");
            let runtime_config_path = if config_path.exists() {
                config_path.clone()
            } else {
                backend_dir
                    .parent()
                    .unwrap_or(&backend_dir)
                    .join("inquira.toml")
            };
            let config = load_config(&runtime_config_path);
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
                    .unwrap_or_else(|| "local_subprocess".to_string())
            );
            let venv_path = data_dir.join(".venv");
            let runner_venv_name = config
                .execution
                .as_ref()
                .and_then(|e| e.runner.as_ref())
                .and_then(|r| r.venv_name.clone())
                .unwrap_or_else(|| ".runner-venv".to_string());
            let runner_venv_path = data_dir.join(runner_venv_name);

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

            let execution_provider = config
                .execution
                .as_ref()
                .and_then(|e| e.provider.clone())
                .unwrap_or_else(|| "local_subprocess".to_string())
                .to_lowercase();
            if execution_provider == "local_safe_runner" {
                app.emit("backend-status", "Preparing isolated code runner...").ok();
                if let Err(e) = bootstrap_runner_env(&uv_bin, &runner_venv_path, &config) {
                    log::error!("Runner bootstrap failed: {}", e);
                    app.emit("backend-status", &format!("Runner setup failed: {}", e))
                        .ok();
                    return Ok(());
                }
            }

            // Phase 2: Start the backend
            app.emit("backend-status", "Starting backend...").ok();
            let runner_python = if execution_provider == "local_safe_runner" {
                Some(python_bin_from_venv(&runner_venv_path))
            } else {
                None
            };

            match start_backend(
                &uv_bin,
                &backend_dir,
                &venv_path,
                runner_python.as_ref(),
                &config,
                &runtime_config_path,
            ) {
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
