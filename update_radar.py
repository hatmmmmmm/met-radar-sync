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
                
                # Capture exact 5-minute file window
                time_match = re.search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})", latest_filename)
                if time_match:
                    year, month, day, hour, minute = time_match.groups()
                    radar_time_human = f"{year}-{month}-{day} {hour}:{minute} UTC"
                
                img_resp = requests.get(target_image_url, headers=headers, timeout=20)
                if img_resp.status_code == 200:
                    if os.path.exists("latest_radar.png"):
                        os.remove("latest_radar.png")
                    with open("latest_radar.png", "wb") as f:
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

    forecast_node = ET.SubElement(root, "budapest_forecast")
    
    try:
        odp_focus_url = "https://odp.met.hu/weather/nwp/FOCUS/focus.json"
        print("Reading ODP FOCUS structural forecast metrics...")
        focus_data = requests.get(odp_focus_url, headers=headers, timeout=15).json()
        
        # Isolate Budapest forecast matrices
        if "Budapest" in focus_data:
            bp_forecast = focus_data["Budapest"]
            
            # loop through the keys inside the data dictionary dynamically
            for day_key, day_metrics in sorted(bp_forecast.items()):
                # Strips out generic structural elements if they appear, keeping dates (e.g. "2026-07-08")
                if not re.match(r"\d{4}-\d{2}-\d{2}", day_key):
                    continue
                    
                day_element = ET.SubElement(forecast_node, "day", date=day_key)
                
                # Extract structural keys directly mapped from the chart layout
                ET.SubElement(day_element, "temp_max").text = f"{day_metrics.get('Tmax', 'N/A')}°C"
                ET.SubElement(day_element, "temp_min").text = f"{day_metrics.get('Tmin', 'N/A')}°C"
                ET.SubElement(day_element, "wind_speed_max").text = f"{day_metrics.get('Wmax', 'N/A')} km/h"
                ET.SubElement(day_element, "wind_speed_avg").text = f"{day_metrics.get('Wavg', 'N/A')} km/h"
                ET.SubElement(day_element, "wind_direction").text = str(day_metrics.get("Wdir", "N/A"))
                ET.SubElement(day_element, "cloud_icon_index").text = str(day_metrics.get("weather_type", "N/A"))
                ET.SubElement(day_element, "precipitation_mm").text = f"{day_metrics.get('Precip', '0')} mm"
        else:
            print("Budapest segment was not found in focus.json file.")
    except Exception as e:
        print(f"Failed parsing numerical forecast grid: {e}")

    # ==========================================
    # 3. EXPORT CLEAN FORMATTED XML ASSET
    # ==========================================
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")
    
    with open("weather_data.xml", "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    print("Success! Multi-day matrix written to weather_data.xml.")

if __name__ == "__main__":
    main()
