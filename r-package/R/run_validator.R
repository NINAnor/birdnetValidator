#' Launch the BirdNET Validator app
#'
#' Opens an interactive Streamlit app in your browser where you can listen to
#' audio clips and validate species detections made by BirdNET.
#'
#' On first use, this function automatically installs the required Python
#' package (`birdnet-validator`) into a dedicated virtual environment.
#'
#' @param audio_dir Path to the directory containing audio files (local path or
#'   S3 URI).
#' @param results_dir Path to the directory containing BirdNET result files
#'   (local path or S3 URI).
#' @param output_dir Path where validation CSVs will be saved (local path or
#'   S3 URI).
#' @param s3_endpoint_url S3 endpoint URL (only needed for S3 paths).
#' @param s3_access_key S3 access key (only needed for S3 paths).
#' @param s3_secret_key S3 secret key (only needed for S3 paths).
#' @param port Port to run the app on (default: 8501).
#' @param open_browser Whether to open the browser automatically (default:
#'   TRUE).
#'
#' @export
#'
#' @examples
#' \dontrun{
#' run_validator(
#'   audio_dir = "/path/to/audio",
#'   results_dir = "/path/to/results",
#'   output_dir = "/path/to/output"
#' )
#' }
run_validator <- function(audio_dir,
                          results_dir,
                          output_dir,
                          s3_endpoint_url = "",
                          s3_access_key = "",
                          s3_secret_key = "",
                          port = 8501L,
                          open_browser = TRUE) {

  .ensure_python_env()

  reticulate::use_virtualenv("birdnet-validator", required = TRUE)

  bv <- reticulate::import("birdnet_validator")

  bv$run(
    audio_dir = audio_dir,
    results_dir = results_dir,
    output_dir = output_dir,
    s3_endpoint_url = s3_endpoint_url,
    s3_access_key = s3_access_key,
    s3_secret_key = s3_secret_key,
    port = as.integer(port),
    open_browser = open_browser
  )
}


#' Update the BirdNET Validator Python package
#'
#' Removes the existing Python environment and reinstalls from GitHub.
#' Run this after the package has been updated on GitHub.
#'
#' @export
#'
#' @examples
#' \dontrun{
#' update_validator()
#' }
update_validator <- function() {
  .setup_windows_venv_root()

  if (reticulate::virtualenv_exists("birdnet-validator")) {
    message("Removing old environment...")
    reticulate::virtualenv_remove("birdnet-validator", confirm = FALSE)
  }

  .ensure_python_env()
  message("Done! Run run_validator() to start the app.")
}


#' @keywords internal
.setup_windows_venv_root <- function() {
  if (.Platform$OS.type == "windows") {
    safe_root <- file.path(Sys.getenv("LOCALAPPDATA"), ".virtualenvs")
    if (!dir.exists(safe_root)) {
      dir.create(safe_root, recursive = TRUE)
    }
    Sys.setenv(WORKON_HOME = safe_root)
  }
}


#' @keywords internal
.ensure_python_env <- function() {
  .setup_windows_venv_root()

  if (!reticulate::virtualenv_exists("birdnet-validator")) {
    message("Setting up Python environment (first time only)...")
    reticulate::virtualenv_create("birdnet-validator")
    reticulate::virtualenv_install(
      "birdnet-validator",
      packages = "birdnet-validator @ git+https://github.com/NINAnor/birdnetValidator.git",
      pip_options = c("--no-cache-dir")
    )
    message("Setup complete!")
  }
}
