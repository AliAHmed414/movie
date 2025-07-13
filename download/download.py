import os
import shutil
import time
import libtorrent as lt

async def download_libtorrent(download_dir, download_target, renamed_folder="downloaded_content"):
    """
    Download a file using libtorrent, rename the result folder, and return new path.
    """
    try:
        os.makedirs(download_dir, exist_ok=True)

        # Create session
        ses = lt.session()
        ses.listen_on(6881, 6891)
        
        # Add torrent
        if download_target.startswith('magnet:'):
            params = lt.parse_magnet_uri(download_target)
            params.save_path = download_dir
            params.flags = lt.torrent_flags.duplicate_is_error | lt.torrent_flags.auto_managed
            h = ses.add_torrent(params)
        else:
            # Assume it's a .torrent file
            info = lt.torrent_info(download_target)
            h = ses.add_torrent({
                'ti': info,
                'save_path': download_dir,
                'flags': lt.torrent_flags.duplicate_is_error | lt.torrent_flags.auto_managed
            })

        print(f"Starting download: {h.name()}")
        
        # Wait for download to complete
        slow_speed_count = 0
        while not h.is_seed():
            s = h.status()
            
            # Print progress
            progress = s.progress * 100
            speed_kbs = s.download_rate / 1000
            print(f'\rProgress: {progress:.1f}% - {speed_kbs:.1f} kB/s', end='')
            
            # Check if download is too slow (less than 50 kB/s for 30 seconds)
            if speed_kbs < 50:
                slow_speed_count += 1
                if slow_speed_count >= 30:  # 30 seconds of slow download
                    print(f"\nDownload too slow ({speed_kbs:.1f} kB/s), cancelling...")
                    ses.remove_torrent(h)
                    return None
            else:
                slow_speed_count = 0  # Reset counter if speed improves
            
            # Check if download is complete
            if s.state == lt.torrent_status.seeding:
                break
                
            time.sleep(1)
        
        print(f"\nDownload completed: {h.name()}")
        
        # Find the downloaded folder
        torrent_name = h.name()
        original_path = os.path.join(download_dir, torrent_name)
        new_path = os.path.join(download_dir, renamed_folder)
        
        # Remove session
        ses.remove_torrent(h)
        
        # Rename the folder if it exists
        if os.path.exists(original_path):
            if os.path.exists(new_path):
                shutil.rmtree(new_path)  # Remove if already exists
            os.rename(original_path, new_path)
            return new_path
        else:
            # If no specific folder was created, return the download directory
            return os.path.abspath(download_dir)

    except Exception as e:
        print(f"libtorrent failed to download the file: {e}")
        return None