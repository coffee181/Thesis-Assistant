mod backend_process;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            app.manage(backend_process::BackendProcess::start());
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to run Knowledge Agent");
}
