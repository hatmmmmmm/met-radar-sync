import os
import time
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom

def parse_met_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.met.hu/"
    }
    
    weather_data = {
        "radar_timestamp": "Unknown",
        "bp_condition": "N/A",
        "bp_temp": "N/A",
        "forecast_summary": ""
    }
    
    session = requests.Session()
    
    try:
        # 1. Pull current data directly from the main desktop landing page
        main_resp = session.get("https://www.met.hu/", headers=headers, timeout=15)
        if main_resp.status_code == 200:
            soup = BeautifulSoup(main_resp.text, 'html.parser')
            
            # Find the element by looking for strings containing 'Budapest' safely
            all_text_nodes = soup.find_all(text=True)
            for node in all_text_nodes:
                if "Budapest" in node and "·" in node:
                    text_line = node.strip()
                    # e.g., "Budapest kissé felhős · 26°C"
                    parts = text_line.split("·")
                    if len(parts) >= 2:
                        weather_data["bp_condition"] = parts[0].replace("Budapest", "").strip()
                        weather_data["bp_temp"] = parts[1].strip()
                    break

            # 2. Gather structural forecast segments from the overview page
            forecast_list = []
            for item in soup.find_all(text=True):
                # Target the embedded forecast strings like '2026.07.08. 15, 22°C'
                if any(day_marker in item for day_marker in ["Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap", "Hétfő", "Kedd"]):
                    clean_f = item.strip().replace("\n", " ").replace("  ", " ")
                    if clean_f and clean_f not in forecast_list:
                        forecast_list.append(clean_f)
            
            if forecast_list:
                # Filter down to the immediate upcoming forecast sequences
                weather_data["forecast_summary"] = " | ".join(forecast_list[:6])

    except Exception as e:
        print(f"Error parsing text blocks: {e}")

    try:
        # 3. Pull time signature layer from the desktop radar view
        radar_resp = session.get("https://www.met.hu/idojaras/aktualis_idojaras/radar/", headers=headers, timeout=15)
        if radar_resp.status_code == 200:
            radar_soup = BeautifulSoup(radar_resp.text, 'html.parser')
            for node in radar_soup.find_all(text=True):
                if "(" in node and "UTC)" in node:
                    weather_data["radar_timestamp"] = node.strip()
                    break
    except Exception as e:
        print(f"Error extracting radar time signature: {e}")
        
    return weather_data

def download_radar_image():
    # Direct high-resolution desktop radar image array link 
    img_url = "https://www.met.hu/img/radar/rccmax.idoido.png"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.met.hu/idojaras/aktualis_idojaras/radar/"
    }
    
    # Strictly force a cache refresh via query parameters
    cache_buster_url = f"{img_url}?t={int(time.time())}"
    print(f"Requesting full desktop map composite: {cache_buster_url}")
    
    try:
        resp = requests.get(cache_buster_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            # Delete any stale asset if it exists to make sure it overwrites cleanly
            if os.path.exists("latest_radar.png"):
                os.remove("latest_radar.png")
                
            with open("latest_radar.png", "wb") as f:
                f.write(resp.content)
            print("Successfully updated desktop radar layout.")
    except Exception as e:
        print(f"Image transfer failure: {e}")

def create_xml_payload(data):
    root = ET.Element("trmnl_data")
    
    meta = ET.SubElement(root, "metadata")
    fetched_epoch = ET.SubElement(meta, "fetched_at_epoch")
    fetched_epoch.text = str(int(time.time()))
    fetched_human = ET.SubElement(meta, "fetched_at_human")
    fetched_human.text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    radar_obs = ET.SubElement(meta, "radar_observed_time")
    radar_obs.text = data["radar_timestamp"]
    
    current = ET.SubElement(root, "budapest_current")
    temp = ET.SubElement(current, "temperature")
    temp.text = data["bp_temp"]
    cond = ET.SubElement(current, "condition")
    cond.text = data["bp_condition"]
    
    forecasts = ET.SubElement(root, "forecasts")
    forecasts.text = data["forecast_summary"]
    
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")
    
    with open("weather_data.xml", "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    print("Successfully built weather_data.xml")

def main():
    download_radar_image()
    data = parse_met_data()
    create_xml_payload(data)

if __name__ == "__main__":
    main()
