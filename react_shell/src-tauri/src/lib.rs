use std::os::windows::process::CommandExt;
use std::sync::Mutex;
use tauri::{Emitter, Manager};
use tauri_plugin_shell::process::CommandChild;

/// Holds the running pdf-bridge sidecar so it can be killed explicitly when
/// the app exits. Dropping a `CommandChild` does NOT kill the underlying
/// Windows process on its own, so without this the sidecar (and, since it's
/// a PyInstaller onefile build, its unpacked child process too) is left
/// running in the background after the window closes.
struct BridgeSidecar(Mutex<Option<CommandChild>>);
struct InitialPdfPath(Mutex<Option<String>>);

/// Detect whether the app was launched by Windows file association (e.g. double-clicking
/// a .pdf file in Explorer).  When that happens Windows passes the file path as the
/// first CLI argument after the executable itself.
fn get_pdf_arg() -> Option<String> {
    let args: Vec<String> = std::env::args().collect();
    // args[0] is the executable; args[1] (if present) should be the file path.
    if let Some(path) = args.get(1) {
        let p = std::path::Path::new(path);
        if p.exists() && p.extension().map(|e| e.eq_ignore_ascii_case("pdf")).unwrap_or(false) {
            return Some(path.clone());
        }
    }
    None
}

#[tauri::command]
fn get_initial_pdf_path(state: tauri::State<'_, InitialPdfPath>) -> Option<String> {
    state.0.lock().unwrap().clone()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Capture the PDF path before the builder consumes the environment.
    let pdf_arg = get_pdf_arg();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![get_initial_pdf_path])
        .setup(move |app| {
            use tauri_plugin_shell::ShellExt;

            // The sidecar is built from the existing Python/PyMuPDF core.  It binds
            // only to 127.0.0.1, so the React UI stays a local desktop application.
            let (_rx, bridge_child) = app.shell().sidecar("pdf-bridge")?.spawn()?;
            app.manage(BridgeSidecar(Mutex::new(Some(bridge_child))));
            app.manage(InitialPdfPath(Mutex::new(pdf_arg.clone())));

            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // If the app was opened via file association, emit the PDF path to the
            // main window once the webview is ready.  The React frontend listens for
            // the "open-pdf" event and calls the bridge to load the file.
            if let Some(path) = pdf_arg {
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    // Give the webview a moment to finish loading before we emit.
                    std::thread::sleep(std::time::Duration::from_millis(1500));
                    if let Some(window) = handle.get_webview_window("main") {
                        let _ = window.emit("open-pdf", path);
                    }
                });
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        // Kill the pdf-bridge sidecar whenever the app is actually shutting
        // down, so no orphaned pdf-bridge.exe process is left running.
        if matches!(
            event,
            tauri::RunEvent::ExitRequested { .. } | tauri::RunEvent::Exit
        ) {
            if let Some(state) = app_handle.try_state::<BridgeSidecar>() {
                if let Some(child) = state.0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
            kill_pdf_bridge_tree();
        }
    });
}

/// `CommandChild::kill()` only terminates the direct child process it holds
/// a handle to. The bridge is built with PyInstaller `--onefile`, which on
/// Windows runs as a small bootloader that unpacks itself and launches a
/// *second*, separate process to actually run the Python code. Killing the
/// bootloader does not kill that grandchild, so it's left running (still
/// bound to the bridge port) after the app closes. `taskkill /T` kills the
/// whole process tree by image name, which reliably takes out both. This
/// app is the only thing that spawns pdf-bridge.exe, so it's safe to target
/// every instance of it rather than tracking PIDs through the bootloader.
fn kill_pdf_bridge_tree() {
    let _ = std::process::Command::new("taskkill")
        .args(["/F", "/IM", "pdf-bridge.exe", "/T"])
        .creation_flags(0x08000000) // CREATE_NO_WINDOW
        .status();
}
