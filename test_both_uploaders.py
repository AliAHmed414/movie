#!/usr/bin/env python3
"""
Test script to run both OK.ru and Dzen uploaders simultaneously
"""
import threading
import time
from uploader.third.ok import main_with_path as ok_upload
from uploader.third.dzen import main_with_path as dzen_upload

def test_ok_upload():
    print("🟦 Starting OK.ru upload...")
    result = ok_upload("/home/kda/comdy.mp4")
    print(f"🟦 OK.ru result: {result}")
    return result

def test_dzen_upload():
    print("🟨 Starting Dzen upload...")
    result = dzen_upload("/home/kda/comdy.mp4", "Test Comedy Video")
    print(f"🟨 Dzen result: {result}")
    return result

def main():
    print("🚀 Testing simultaneous uploads...")
    
    # Create threads for both uploads
    ok_thread = threading.Thread(target=test_ok_upload, name="OK-Upload")
    dzen_thread = threading.Thread(target=test_dzen_upload, name="Dzen-Upload")
    
    # Start both threads simultaneously
    start_time = time.time()
    ok_thread.start()
    dzen_thread.start()
    
    # Wait for both to complete
    ok_thread.join()
    dzen_thread.join()
    
    end_time = time.time()
    print(f"✅ Both uploads completed in {end_time - start_time:.1f} seconds")

if __name__ == "__main__":
    main()