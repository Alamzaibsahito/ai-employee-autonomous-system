import os
import datetime

def check_log_file(filepath, max_size_mb=1):
    """
    Checks if a log file exceeds a specified size. If it does, the file is renamed
    with a timestamp, and a new empty file with the original name is created.

    Args:
        filepath (str): The full path to the log file to check.
        max_size_mb (int): The maximum allowed size for the log file in megabytes.
    """
    
    # Convert max_size_mb to bytes for comparison
    max_size_bytes = max_size_mb * 1024 * 1024

    # Check if the file exists
    if not os.path.exists(filepath):
        print(f"Log file not found: {filepath}. Skipping check.")
        return

    # Get the current size of the file
    current_size = os.path.getsize(filepath)

    # If the file is larger than the maximum allowed size
    if current_size > max_size_bytes:
        print(f"Log file {filepath} ({(current_size / (1024 * 1024)):.2f} MB) exceeds {max_size_mb} MB.")

        # Generate a timestamp for the new filename
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
        
        # Split the original filepath into directory, base name, and extension
        dirname, basename = os.path.split(filepath)
        filename_without_ext, extension = os.path.splitext(basename)

        # Create the new timestamped filename
        new_filename = f"{filename_without_ext}_{timestamp}{extension}"
        new_filepath = os.path.join(dirname, new_filename)

        # Rename the old log file
        try:
            os.rename(filepath, new_filepath)
            print(f"Renamed '{filepath}' to '{new_filepath}'.")

            # Create a new, empty log file with the original name
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('')
            print(f"Created a new, empty log file: '{filepath}'.")
        except OSError as e:
            print(f"Error managing log file {filepath}: {e}")
    else:
        print(f"Log file {filepath} ({(current_size / (1024 * 1024)):.2f} MB) is within limits.")

if __name__ == "__main__":
    print("Starting log management script...")
    
    # Define the log files to check
    # Note: 'System_Log.md' is in the root directory, 'watcher_errors.log' is in the 'Logs' subfolder.
    log_file_system_log = "System_Log.md"
    log_file_watcher_errors = "Logs/watcher_errors.log"

    # Ensure the 'Logs' directory exists for watcher_errors.log, just in case
    # This is a good practice for scripts that interact with specific directories.
    os.makedirs("Logs", exist_ok=True)

    # Check each log file
    check_log_file(log_file_system_log)
    check_log_file(log_file_watcher_errors)
    
    print("Log management script finished.")
