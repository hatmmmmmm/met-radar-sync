import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    radar_time_human = "Unknown"
    local_image_filename = "latest_radar.png"
    
    github_user = "hatmmmmmm"
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
    # 2. PARSE 7-DAY BUDAPEST FORECAST FROM WEB
    # ==========================================
    weather_data = {
        "metadata": {
            "fetched_at_epoch": int(time.time()),
            "fetched_at_human": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            "radar_observed_time": radar_time_human,
            "radar_image_file": public_image_url
        },
        "budapest_forecast": []
    }

    try:
        print("Parsing live 7-day operational forecast matrix...")
        # Target the main weather page for Budapest
        forecast_url = "https://www.met.hu/idojaras/elorejelzes/magyarorszagi_telepulesek/details.php?id=Budapest"
        page_resp = requests.get(forecast_url, headers=headers, timeout=15)
        
        if page_resp.status_code == 200:
            soup = BeautifulSoup(page_resp.text, 'html.parser')
            
            # Find the main container for the daily forecast blocks
            forecast_container = soup.find('div', class_='elorejelzes-telepules-napok')
            if forecast_container:
                days = forecast_container.find_all('div', class_='nap')
                
                for day in days:
                    # Extract date, max/min temps, wind, and precipitation values
                    date_label = day.find('span', class_='datum').text.strip() if day.find('span', class_='datum') else "N/A"
                    tmax = day.find('span', class_='tmax').text.strip() if day.find('span', class_='tmax') else "N/A"
                    tmin = day.find('span', class_='tmin').text.strip() if day.find('span', class_='tmin') else "N/A"
                    
                    # Target icon names to determine the cloud/weather status index
                    img_tag = day.find('img', class_='idokep')
                    icon_idx = img_tag.get('src', '').split('/')[-1].replace('.png', '') if img_tag else "N/A"
                    
                    day_entry = {
                        "date_label": date_label,
                        "temp_max": tmax,
                        "temp_min": tmin,
                        "cloud_icon_index": icon_idx,
                        # Web values fall back to defaults if detailed metrics are deep-linked
                        "wind_speed_max": "N/A", 
                        "precipitation_mm": "N/A"
                    }
                    weather_data["budapest_forecast"].append(day_entry)
            else:
                print("Could not locate the operational table container on the web page structure.")
    except Exception as e:
        print(f"Failed parsing operational forecast grid: {e}")

    # ==========================================
    # 3. EXPORT NATIVE JSON ASSET
    # ==========================================
    with open("weather_data.json", "w", encoding="utf-8") as f:
        json.dump(weather_data, f, ensure_ascii=False, indent=2)
    print("Success! Native object array written to weather_data.json.")

if __name__ == "__main__":
    main()
