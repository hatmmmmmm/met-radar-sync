import os
import re
import time
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    radar_time_human = "Unknown"
    local_image_filename = "latest_radar.png"
    
    # Configuration for your public GitHub asset link
    github_user = "hatmmmmmmm"
    github_repo = "met-radar-sync"
    public_image_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/main/{local_image_filename}"

    # ==========================================
    # 1. DOWNLOAD LATEST HIGH-RES ODP RADAR
    # ==========================================
    odp_radar_dir = "https://odp.met.hu/weather/radar/composite/png/refl2D/"
    print("Connecting to ODP Radar Engine...")
    
    try:
        dir_resp = requests.get(odp_radar_dir, headers=headers, timeout=15)
        if dir_resp.status_code == 200:
            soup = BeautifulSoup(dir_resp.text, 'html.parser')
            png_links = [link.get('href', '') for link in soup.find_all('a') 
                         if link.get('href', '').startswith("radar_composite-refl2D-") and link.get('href', '').endswith(".png")]
            
            if png_links:
                latest_filename = sorted(png_links)[-1]
                target_image_url = odp_radar_dir + latest_filename
                
                # Capture exact 5-minute file window from filename
                time_match = re.search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})", latest_filename)
                if time_match:
                    year, month, day, hour, minute = time_match.groups()
                    radar_time_human = f"{year}-{month}-{day} {hour}:{minute} UTC"
                
                img_resp = requests.get(target_image_url, headers=headers, timeout=20)
                if img_resp.status_code == 200:
                    if os.path.exists(local_image_filename):
                        os.remove(local_image_filename)
                    with open(local_image_filename, "wb") as f:
                        f.write(img_resp.content)
                    print(f"Verified Radar Map pulled: {latest_filename}")
    except Exception as e:
        print(f"Radar tracking failed: {e}")

    # ==========================================
    # 2. PARSE THE 7-DAY GRID DATA FROM ODP JSON
    # ==========================================
    root = ET.Element("trmnl_data")
    
    # Generate clean global metadata nodes
    meta = ET.SubElement(root, "metadata")
    ET.SubElement(meta, "fetched_at_epoch").text = str(int(time.time()))
    ET.SubElement(meta, "fetched_at_human").text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    ET.SubElement(meta, "radar_observed_time").text = radar_time_human
    ET.SubElement(meta, "radar_image_file").text = public_image_url

    forecast_node = ET.SubElement(root, "budapest_forecast")
    
    try:
        odp_focus_url = "https://odp.met.hu/weather/nwp/FOCUS/focus.json"
        print("Reading ODP FOCUS structural forecast metrics...")
        focus_data = requests.get(odp_focus_url, headers=headers, timeout=15).json()
        
        if "Budapest" in focus_data:
            bp
