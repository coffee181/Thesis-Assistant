use std::collections::HashMap;
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

pub const BACKEND_ADDR: &str = "127.0.0.1:8765";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BackendLaunch {
    pub program: PathBuf,
    pub args: Vec<String>,
    pub cwd: PathBuf,
}

pub struct BackendProcess {
    child: Mutex<Option<Child>>,
}

impl BackendProcess {
    pub fn start() -> Self {
        if is_backend_port_open(BACKEND_ADDR) {
            return Self::empty();
        }

        let current_dir = match std::env::current_dir() {
            Ok(path) => path,
            Err(error) => {
                eprintln!("could not resolve current directory for backend launch: {error}");
                return Self::empty();
            }
        };
        let env = std::env::vars().collect::<HashMap<_, _>>();
        let Some(launch) = resolve_backend_launch_from_env(&current_dir, &env) else {
            eprintln!("could not resolve backend launch command");
            return Self::empty();
        };

        let child = Command::new(&launch.program)
            .args(&launch.args)
            .current_dir(&launch.cwd)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn();

        match child {
            Ok(child) => Self {
                child: Mutex::new(Some(child)),
            },
            Err(error) => {
                eprintln!(
                    "could not start backend process {}: {error}",
                    launch.program.display()
                );
                Self::empty()
            }
        }
    }

    fn empty() -> Self {
        Self {
            child: Mutex::new(None),
        }
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        let Ok(mut child_guard) = self.child.lock() else {
            return;
        };
        let Some(mut child) = child_guard.take() else {
            return;
        };
        let _ = child.kill();
        let _ = child.wait();
    }
}

pub fn is_backend_port_open(addr: &str) -> bool {
    let Ok(socket_addr) = addr.parse() else {
        return false;
    };
    TcpStream::connect_timeout(&socket_addr, Duration::from_millis(150)).is_ok()
}

pub fn resolve_backend_launch_from_env(
    current_dir: &Path,
    env: &HashMap<String, String>,
) -> Option<BackendLaunch> {
    if let Some(program) = env.get("KA_BACKEND_PROGRAM").filter(|value| !value.trim().is_empty()) {
        return Some(BackendLaunch {
            program: PathBuf::from(program),
            args: env
                .get("KA_BACKEND_ARGS")
                .map(|value| split_args(value))
                .unwrap_or_default(),
            cwd: current_dir.to_path_buf(),
        });
    }

    let repo_root = find_repo_root(current_dir)?;
    Some(BackendLaunch {
        program: repo_root
            .join(".venv")
            .join("Scripts")
            .join("python.exe"),
        args: vec![
            "-m".to_string(),
            "uvicorn".to_string(),
            "knowledge_agent.main:app".to_string(),
            "--host".to_string(),
            "127.0.0.1".to_string(),
            "--port".to_string(),
            "8765".to_string(),
        ],
        cwd: repo_root,
    })
}

fn split_args(value: &str) -> Vec<String> {
    value
        .split_whitespace()
        .map(ToString::to_string)
        .collect()
}

fn find_repo_root(current_dir: &Path) -> Option<PathBuf> {
    let mut candidate = Some(current_dir);
    while let Some(path) = candidate {
        if path.join("backend").join("pyproject.toml").is_file()
            && path.join("apps").join("desktop").join("package.json").is_file()
        {
            return Some(path.to_path_buf());
        }
        candidate = path.parent();
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_repo() -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("ka-launch-test-{nonce}"));
        fs::create_dir_all(root.join("backend")).unwrap();
        fs::create_dir_all(root.join("apps/desktop/src-tauri")).unwrap();
        fs::write(root.join("backend/pyproject.toml"), "").unwrap();
        fs::write(root.join("apps/desktop/package.json"), "{}").unwrap();
        root
    }

    #[test]
    fn resolves_development_backend_from_repo_root() {
        let root = temp_repo();
        let cwd = root.join("apps/desktop/src-tauri");
        let launch = resolve_backend_launch_from_env(&cwd, &HashMap::new()).unwrap();

        assert_eq!(launch.cwd, root);
        assert!(launch.program.ends_with(".venv\\Scripts\\python.exe"));
        assert_eq!(
            launch.args,
            vec![
                "-m",
                "uvicorn",
                "knowledge_agent.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8765"
            ]
        );

        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn explicit_backend_program_and_args_override_development_resolution() {
        let mut env = HashMap::new();
        env.insert(
            "KA_BACKEND_PROGRAM".to_string(),
            "F:\\bundle\\backend.exe".to_string(),
        );
        env.insert(
            "KA_BACKEND_ARGS".to_string(),
            "--host 127.0.0.1 --port 8765".to_string(),
        );

        let launch = resolve_backend_launch_from_env(Path::new("F:\\nowhere"), &env).unwrap();

        assert_eq!(launch.program, PathBuf::from("F:\\bundle\\backend.exe"));
        assert_eq!(launch.args, vec!["--host", "127.0.0.1", "--port", "8765"]);
        assert_eq!(launch.cwd, PathBuf::from("F:\\nowhere"));
    }

    #[test]
    fn reports_unused_backend_port_as_not_running() {
        assert!(!is_backend_port_open("127.0.0.1:9"));
    }
}
