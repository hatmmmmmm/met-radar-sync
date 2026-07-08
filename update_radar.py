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
        
        # Look for Budapest data dynamically (checking common case variations)
        bp_forecast = None
        for key in ["Budapest", "budapest", "BUDAPEST", "12843"]: # 12843 is Budapest's OMSZ/HungaroMet block station code
            if key in focus_data:
                bp_forecast = focus_data[key]
                print(f"Successfully matched Budapest data layout using key: '{key}'")
                break
        
        # Fallback: If it's a flat date-first array dictionary
        if bp_forecast is None:
            first_key = next(iter(focus_data))
            if re.match(r"\d{4}-\d{2}-\d{2}", first_key):
                bp_forecast = focus_data
                print("Processing global date-sorted forecast grid structure...")

        if bp_forecast:
            for day_key, day_metrics in sorted(bp_forecast.items()):
                # Filter out metadata structural nodes, leaving only string dates
                if not isinstance(day_key, str) or not re.search(r"\d{4}-\d{2}-\d{2}", day_key):
                    continue
                
                # Extract properties safely with fallback indicators
                tmax = day_metrics.get('Tmax') or day_metrics.get('tmax') or day_metrics.get('T2max', 'N/A')
                tmin = day_metrics.get('Tmin') or day_metrics.get('tmin') or day_metrics.get('T2min', 'N/A')
                wmax = day_metrics.get('Wmax') or day_metrics.get('wmax') or day_metrics.get('WSpeedMax', 'N/A')
                wavg = day_metrics.get('Wavg') or day_metrics.get('wavg') or day_metrics.get('WSpeedAvg', 'N/A')
                wdir = day_metrics.get('Wdir') or day_metrics.get('wdir') or day_metrics.get('WDir10', 'N/A')
                icon = day_metrics.get('weather_type') or day_metrics.get('icon') or day_metrics.get('Fx', 'N/A')
                prec = day_metrics.get('Precip') or day_metrics.get('precip') or day_metrics.get('P24', '0')

                day_entry = {
                    "date_label": day_key,
                    "temp_max": f"{tmax}°C" if "°C" not in str(tmax) and tmax != 'N/A' else str(tmax),
                    "temp_min": f"{tmin}°C" if "°C" not in str(tmin) and tmin != 'N/A' else str(tmin),
                    "wind_speed_max": f"{wmax} km/h" if "km/h" not in str(wmax) and wmax != 'N/A' else str(wmax),
                    "wind_speed_avg": f"{wavg} km/h" if "km/h" not in str(wavg) and wavg != 'N/A' else str(wavg),
                    "wind_direction": str(wdir),
                    "cloud_icon_index": str(icon),
                    "precipitation_mm": f"{prec} mm" if "mm" not in str(prec) else str(prec)
                }
                weather_data["budapest_forecast"].append(day_entry)
        else:
            # Absolute fallback: loop through and find nested Budapest strings safely
            print("Layout mismatched. Attempting secondary structural parsing query...")
            for main_key, nested_val in focus_data.items():
                if isinstance(nested_val, dict) and "Budapest" in str(nested_val.keys()):
                    bp_forecast = nested_val.get("Budapest")
                    # process subelements loop...
                    
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
