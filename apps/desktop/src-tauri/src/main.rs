mod backend_process;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let resource_dir = app.path().resource_dir().ok();
            app.manage(backend_process::BackendProcess::start(resource_dir));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to run Knowledge Agent");
}
