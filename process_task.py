import os
import shutil
import re
from datetime import datetime

def process_task():
    """
    Process tasks in the Needs_Action folder by:
    1. Opening the Needs_Action folder
    2. Reading each task file
    3. Understanding the task from its content
    4. Marking its status as completed inside the file
    5. Moving the file to the Done folder
    6. Updating Dashboard.md to add the task under "Completed Tasks" and remove from "Pending Tasks"
    7. Appending a short entry to System_Log.md describing what was completed
    """
    needs_action_folder = "Needs_Action"
    done_folder = "Done"
    
    # Create folders if they don't exist
    os.makedirs(needs_action_folder, exist_ok=True)
    os.makedirs(done_folder, exist_ok=True)
    
    # Get all task files in Needs_Action folder
    task_files = [f for f in os.listdir(needs_action_folder) if f.endswith('.md')]
    
    if not task_files:
        print("No tasks found in Needs_Action folder.")
        return
    
    for task_file in task_files:
        task_path = os.path.join(needs_action_folder, task_file)
        
        # Read the task file content
        with open(task_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract filename from the YAML frontmatter
        filename_match = re.search(r'filename: (.+)', content)
        original_filename = filename_match.group(1) if filename_match else task_file
        
        # Update the status to completed in the YAML frontmatter
        updated_content = re.sub(r'status: pending', 'status: completed', content)
        
        # Write the updated content back to the file
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        # Move the file to the Done folder
        done_path = os.path.join(done_folder, task_file)
        shutil.move(task_path, done_path)
        
        # Update Dashboard.md
        update_dashboard(original_filename)
        
        # Update System_Log.md
        update_system_log(original_filename)
        
        print(f"Processed task: {original_filename}")

def update_dashboard(task_name):
    """
    Update Dashboard.md to add the task under "Completed Tasks" and remove from "Pending Tasks"
    """
    dashboard_path = "Dashboard.md"
    
    # Read the current dashboard content
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard_content = f.read()
    
    # Add the task to Completed Tasks section
    completed_section_start = dashboard_content.find("## Completed Tasks")
    if completed_section_start != -1:
        # Find the end of the Completed Tasks section (next section or end of file)
        next_section_start = dashboard_content.find("## ", completed_section_start + len("## Completed Tasks"))
        if next_section_start == -1:
            next_section_start = len(dashboard_content)
        
        # Extract the completed tasks section
        completed_tasks_section = dashboard_content[completed_section_start:next_section_start]
        
        # Create the new completed task entry
        new_completed_entry = f"- [x] {task_name}"
        
        # Check if the task is already listed in completed tasks
        if new_completed_entry not in completed_tasks_section:
            # Insert the new completed task entry after the section header
            insert_pos = completed_section_start + len("## Completed Tasks") + 1
            dashboard_content = dashboard_content[:insert_pos] + f"\n{new_completed_entry}" + dashboard_content[insert_pos:]
    
    # Remove the task from Pending Tasks section
    pending_section_start = dashboard_content.find("## Pending Tasks")
    if pending_section_start != -1:
        # Find the end of the Pending Tasks section (next section or end of file)
        next_section_start = dashboard_content.find("## ", pending_section_start + len("## Pending Tasks"))
        if next_section_start == -1:
            next_section_start = len(dashboard_content)
        
        # Extract the pending tasks section
        pending_tasks_section = dashboard_content[pending_section_start:next_section_start]
        
        # Create the pending task entry to remove
        pending_entry_to_remove = f"- [ ] {task_name}"
        
        # Remove the pending task entry if it exists
        if pending_entry_to_remove in pending_tasks_section:
            # Find the position of the pending entry
            entry_pos = pending_tasks_section.find(pending_entry_to_remove)
            # Find the end of the line containing the entry
            entry_end = pending_tasks_section.find('\n', entry_pos)
            if entry_end == -1:  # If it's the last line
                entry_end = len(pending_tasks_section)
            else:
                entry_end += 1  # Include the newline character
            
            # Remove the entry from the section
            updated_pending_section = pending_tasks_section[:entry_pos] + pending_tasks_section[entry_end:]
            
            # Update the dashboard content with the modified pending section
            dashboard_content = dashboard_content[:pending_section_start] + updated_pending_section + dashboard_content[next_section_start:]
    
    # Write the updated dashboard content back to the file
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(dashboard_content)

def update_system_log(task_name):
    """
    Append a short entry to System_Log.md describing what was completed
    """
    log_path = "System_Log.md"
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create the log entry
    log_entry = f"{timestamp} - Completed task: {task_name}\n"
    
    # Append the log entry to the activity log section
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry)

if __name__ == "__main__":
    process_task()