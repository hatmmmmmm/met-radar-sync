import os
import time
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from xml.dom import minidom

def clean_xml_string(element):
    """Returns a pretty-printed XML string for TRMNL parsing."""
    rough_string = ET.tostring(element, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def main():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.met.hu/"
    }
    
    # ---------------------------------------------------------
    # 1. DOWNLOAD THE FULL-SIZE MAIN RADAR ASSET
    # ---------------------------------------------------------
    radar_base_url = "https://www.met.hu/img/radar/rccmax.idoido.png"
    timestamp = int(time.time())
    radar_url = f"{radar_base_url}?t={timestamp}"
    
    print(f"Fetching full-size desktop radar image from: {radar_url}")
    try:
        img_response = session.get(radar_url, headers=headers, timeout=15)
        if img_response.status_code == 200:
            with open("latest_radar.png", "wb") as f:
                f.write(img_response.content)
            print("Successfully saved full-size latest_radar.png")
        else:
            print(f"Failed to fetch radar image asset: {img_response.status_code}")
    except Exception as e:
        print(f"Error fetching radar image: {e}")

    # ---------------------------------------------------------
    # 2. SCRAPE BUDAPEST WEATHER AND COMPILE THE XML DATA
    # ---------------------------------------------------------
    weather_url = "https://www.met.hu/idojaras/"
    print(f"Scraping current data and forecasts from: {weather_url}")
    
    root_xml = ET.Element("trmnl_data")
    
    # Track metadata stamp of the fetch execution
    meta_xml = ET.SubElement(root_xml, "metadata")
    ET.SubElement(meta_xml, "fetched_at_epoch").text = str(timestamp)
    ET.SubElement(meta_xml, "fetched_at_human").text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    try:
        response = session.get(weather_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Target the current Budapest data panel block
            bp_xml = ET.SubElement(root_xml, "budapest_current")
            
            # Find the element showing current temperature in Budapest
            # The desktop portal groups actual strings inside an identifiable grid or marquee class
            bp_temp = None
            bp_cond = "N/A"
            
            for item in soup.find_all(text=True):
                if "Budapest" in item:
                    # Look globally around parent containers for text siblings matching degrees Celsius
                    parent_text = item.parent.get_text() if item.parent else ""
                    if "°C" in parent_text:
                        # Extract the condition text block strings cleanly
                        parts = [p.strip() for p in parent_text.split("·") if p.strip()]
                        for part in parts:
                            if "Budapest" in part:
                                bp_cond = part.replace("Budapest", "").strip()
                            if "°C" in part:
                                bp_temp = part.strip()
                        break

            ET.SubElement(bp_xml, "temperature").text = bp_temp if bp_temp else "N/A"
            ET.SubElement(bp_xml, "condition").text = bp_cond

            # Extract the 7-day text preview matrix rows
            forecast_xml = ET.SubElement(root_xml, "forecasts")
            forecast_box = soup.find("div", class_="vv-forecast-box") or soup.find("div", id="content")
            
            if forecast_box:
                # Loop through days parsed out of the main grid blocks
                days_found = 0
                for text_node in soup.find_all(text=True):
                    if "2026." in text_node and "°C" in text_node.parent.get_text():
                        full_row = text_node.parent.get_text().strip()
                        # Sanitize whitespace blobs down to single separators
                        clean_row = " ".join(full_row.split())
                        
                        day_item = ET.SubElement(forecast_xml, "day")
                        day_item.set("index", str(days_found))
                        ET.SubElement(day_item, "raw_data").text = clean_row
                        days_found += 1
                        if days_found >= 5: # Limit tree growth down to next 5 days max
                            break
                            
            print("Successfully processed weather dataset.")
        else:
            print(f"Could not load weather portal page payload: {response.status_code}")
    except Exception as e:
        print(f"Error compiling scraping node sequences: {e}")

    # Save out structured layout document directly into workspace root
    xml_output = clean_xml_string(root_xml)
    with open("weather_data.xml", "w", encoding="utf-8") as xml_file:
        xml_file.write(xml_output)
    print("Success! weather_data.xml file output complete.")

if __name__ == "__main__":
    main()
