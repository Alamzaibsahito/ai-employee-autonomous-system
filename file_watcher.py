import os
import time
from datetime import datetime
import re # Import regex for robust checklist parsing

# Import auto planner for automatic plan generation
try:
    from skills.auto_planner import on_task_created
except ImportError:
    try:
        from auto_planner import on_task_created
    except ImportError:
        # Fallback if module not available
        def on_task_created(task_filename, task_content):
            print(f"Task created: {task_filename} (auto-planner not available)")

def build_initial_processed_set():
    """
    Scans 'Needs_Action' and 'Done' folders to build a set of filenames that have
    already been processed. This prevents creating duplicate tasks when the script restarts.
    """
    processed_files = set()
    # List of folders to scan for existing tasks
    folders_to_scan = ["Needs_Action", "Done"]

    print("Building initial set of processed files...")

    for folder in folders_to_scan:
        # Check if the folder exists before trying to scan it
        if not os.path.exists(folder):
            print(f"'{folder}' directory not found, skipping.")
            continue
        
        # Walk through all files in the directory
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            
            # Ensure it's a file, not a directory
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        in_yaml_frontmatter = False
                        # Read line by line to find the 'filename:' entry in the YAML frontmatter
                        for line in f:
                            if line.strip() == "---":
                                if not in_yaml_frontmatter:
                                    in_yaml_frontmatter = True
                                    continue
                                else: # Found second ---, end of frontmatter
                                    break # Exit loop after frontmatter
                            
                            # Only parse lines within the YAML frontmatter
                            if in_yaml_frontmatter and line.strip().startswith("filename:"):
                                # Extract the value after "filename:"
                                original_filename = line.split(":", 1)[1].strip()
                                # Remove quotes if present, e.g., 'client_notes.txt' -> client_notes.txt
                                original_filename = original_filename.strip().strip('"').strip("'")
                                if original_filename:
                                    processed_files.add(original_filename)
                                    break # Found the filename, no need to parse further for this file
                except Exception as e:
                    print(f"Warning: Could not read or parse {filepath}. Error: {e}")
    
    if processed_files:
        print(f"Found {len(processed_files)} previously processed files.")
    else:
        print("No previously processed files found.")
        
    return processed_files

def monitor_inbox():
    """
    Monitors the Inbox folder and creates task files in Needs_Action when new files appear.
    Includes error handling and is restart-safe.
    """
    # Define folder paths
    inbox_folder = "Inbox"
    needs_action_folder = "Needs_Action"
    log_folder = "Logs"
    error_log_path = os.path.join(log_folder, "watcher_errors.log")

    # --- Ensure directories exist ---
    try:
        os.makedirs(inbox_folder, exist_ok=True)
        os.makedirs(needs_action_folder, exist_ok=True)
        os.makedirs(log_folder, exist_ok=True)
    except OSError as e:
        print(f"FATAL ERROR: Could not create necessary directories: {e}")
        return # Exit the function

    # --- Build initial processed files set ---
    # This makes the script restart-safe by not creating duplicate tasks.
    processed_files = build_initial_processed_set()
    
    print("\nStarting file watcher...")
    print(f"Monitoring: {inbox_folder}/")
    print(f"Creating tasks in: {needs_action_folder}/")
    print(f"Logging errors to: {error_log_path}")
    print("Press Ctrl+C to stop\n")
    
    # --- Main Loop with Error Handling ---
    try:
        while True:
            try:
                inbox_files = os.listdir(inbox_folder)
                
                for filename in inbox_files:
                    # --- Skip if file has already been processed ---
                    if filename in processed_files:
                        continue
                    
                    filepath = os.path.join(inbox_folder, filename)
                    
                    if os.path.isfile(filepath):
                        task_filename = f"task_{filename}_{int(time.time())}.md"
                        task_filepath = os.path.join(needs_action_folder, task_filename)

                        with open("plants/task_templete.md", "r", encoding="utf-8") as f:
                            template_content = f.read()

                        # --- Populate the template with dynamic values ---
                        task_content = template_content.replace("<timestamp>", datetime.now().isoformat())
                        # Add Related_files and the new filename entry to the YAML frontmatter
                        # This ensures the filename is explicitly available for parsing on restart
                        task_content = task_content.replace(
                            "Related_files: []", 
                            f"Related_files: [\'Inbox/{filename}\']\nfilename: {filename}"
                        )
                        task_content = task_content.replace("# task title", f"# Task: Review File '{filename}'")
                        task_content = task_content.replace("(Explain the task clearly)", f"A new file '{filename}' was added to the Inbox and requires review.")
                        
                        with open(task_filepath, 'w', encoding='utf-8') as task_file:
                            task_file.write(task_content)

                        # --- Add to set IMMEDIATELY after creation ---
                        processed_files.add(filename)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Created task for: {filename}")
                        
                        # Gold Tier: Automatically generate plan for new task
                        try:
                            on_task_created(task_filename, task_content)
                        except Exception as e:
                            print(f"Warning: Plan generation failed: {e}")
                            # Continue anyway - plan can be generated later by Ralph Loop
            
            except FileNotFoundError as e:
                error_message = f"Template file not found: {e}"
                print(error_message)
                with open(error_log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[{datetime.now().isoformat()}] {error_message}\n")
                time.sleep(60)

            except Exception as e:
                error_message = f"An unexpected error occurred: {e}"
                print(error_message)
                with open(error_log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"[{datetime.now().isoformat()}] {error_message}\n")

            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nFile watcher stopped by user.")
        print("Exiting cleanly...")

if __name__ == "__main__":
    monitor_inbox()
