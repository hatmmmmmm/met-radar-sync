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
    # 2. PARSE THE 7-DAY GRID DATA INTO JSON
    # ==========================================
    # Constructing a clean, primitive dictionary layer
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
        odp_focus_url = "https://odp.met.hu/weather/nwp/FOCUS/focus.json"
        print("Reading ODP FOCUS structural forecast metrics...")
        focus_data = requests.get(odp_focus_url, headers=headers, timeout=15).json()
        
        if "Budapest" in focus_data:
            bp_forecast = focus_data["Budapest"]
            
            for day_key, day_metrics in sorted(bp_forecast.items()):
                if not re.match(r"\d{4}-\d{2}-\d{2}", day_key):
                    continue
                
                day_entry = {
                    "date_label": day_key,
                    "temp_max": f"{day_metrics.get('Tmax', 'N/A')}°C",
                    "temp_min": f"{day_metrics.get('Tmin', 'N/A')}°C",
                    "wind_speed_max": f"{day_metrics.get('Wmax', 'N/A')} km/h",
                    "wind_speed_avg": f"{day_metrics.get('Wavg', 'N/A')} km/h",
                    "wind_direction": str(day_metrics.get("Wdir", "N/A")),
                    "cloud_icon_index": str(day_metrics.get("weather_type", "N/A")),
                    "precipitation_mm": f"{day_metrics.get('Precip', '0')} mm"
                }
                weather_data["budapest_forecast"].append(day_entry)
        else:
            print("Budapest segment was not found in focus.json file.")
    except Exception as e:
        print(f"Failed parsing numerical forecast grid: {e}")

    # ==========================================
    # 3. EXPORT NATIVE JSON ASSET
    # ==========================================
    with open("weather_data.json", "w", encoding="utf-8") as f:
        json.dump(weather_data, f, ensure_ascii=False, indent=2)
    print("Success! Native object array written to weather_data.json.")

if __name__ == "__main__":
    main()
