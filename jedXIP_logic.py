# jedXIP_logic.py
# Handles the logic for creating, reading, and extracting .xip/.xap archives.

import os
import zipfile
from datetime import datetime

class XipManager:
    """Manages all archive operations like create, list, and extract."""

    def list_contents(self, archive_path):
        """Lists the contents of a .xip or .xap archive."""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                content_list = []
                for info in zf.infolist():
                    content_list.append({
                        'filename': info.filename,
                        'size': info.file_size,
                        'modified': datetime(*info.date_time).strftime('%Y-%m-%d %H:%M:%S')
                    })
                return content_list
        except (zipfile.BadZipFile, FileNotFoundError):
            return None

    def extract_archive(self, archive_path, destination_path, progress_queue=None):
        """Extracts all contents of an archive, reporting progress."""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                members = zf.infolist()
                if progress_queue:
                    progress_queue.put({'total': len(members)})
                for member in members:
                    zf.extract(member, destination_path)
                    if progress_queue:
                        progress_queue.put('increment')
            return True
        except (zipfile.BadZipFile, FileNotFoundError):
            return False
            
    def extract_selected(self, archive_path, member_list, destination_path, progress_queue=None):
        """Extracts a specific list of members, reporting progress."""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                if progress_queue:
                    progress_queue.put({'total': len(member_list)})
                for member in member_list:
                    zf.extract(member, destination_path)
                    if progress_queue:
                        progress_queue.put('increment')
            return True
        except Exception as e:
            print(f"Error during selective extraction: {e}")
            return False

    def create_archive(self, source_paths, archive_path, progress_queue=None):
        """Creates a new archive from local file paths, reporting progress."""
        if progress_queue:
            total_files = 0
            for path in source_paths:
                if os.path.isfile(path):
                    total_files += 1
                elif os.path.isdir(path):
                    for _, _, files in os.walk(path):
                        total_files += len(files)
            progress_queue.put({'total': total_files})

        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for source_path in source_paths:
                    if os.path.isfile(source_path):
                        zf.write(source_path, os.path.basename(source_path))
                        if progress_queue: progress_queue.put('increment')
                    elif os.path.isdir(source_path):
                        base_dir = os.path.dirname(source_path)
                        for root, _, files in os.walk(source_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, base_dir)
                                zf.write(file_path, arcname)
                                if progress_queue: progress_queue.put('increment')
            return True
        except Exception as e:
            print(f"Error creating archive: {e}")
            return False

    def create_archive_from_members(self, source_archive_path, member_list, new_archive_path, progress_queue=None):
        """Creates a new archive from selected files within an existing archive."""
        try:
            with zipfile.ZipFile(source_archive_path, 'r') as source_zf:
                full_member_list = set()
                for member_path in member_list:
                    if member_path.endswith('/'): # It's a folder
                        for item in source_zf.infolist():
                            if item.filename.startswith(member_path):
                                full_member_list.add(item.filename)
                    else:
                        full_member_list.add(member_path)

                if progress_queue:
                    progress_queue.put({'total': len(full_member_list)})

                with zipfile.ZipFile(new_archive_path, 'w', zipfile.ZIP_DEFLATED) as dest_zf:
                    for member_name in sorted(list(full_member_list)):
                        if not member_name.endswith('/'):
                            file_data = source_zf.read(member_name)
                            dest_zf.writestr(member_name, file_data)
                        if progress_queue:
                            progress_queue.put('increment')
            return True
        except Exception as e:
            print(f"Error creating archive from members: {e}")
            return False
