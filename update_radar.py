import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from PIL import Image

def process_radar_image(image_path):
    """
    Advanced color isolation using HSV thresholds to completely remove 
    the topographic background map while keeping only vibrant radar rain cells.
    """
    print("Processing radar image with high-precision color isolation...")
    try:
        if not os.path.exists(image_path):
            print(f"Error: Target image {image_path} does not exist.")
            return

        img = Image.open(image_path).convert("RGB")
        pixels = img.load()
        width, height = img.size

        # Create a clean white canvas
        new_img = Image.new("RGB", (width, height), (255, 255, 255))
        new_pixels = new_img.load()

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]

                # Convert RGB to HSV algorithmically
                r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
                max_c = max(r_n, g_n, b_n)
                min_c = min(r_n, g_n, b_n)
                diff = max_c - min_c

                s = (diff / max_c) if max_c != 0 else 0
                v = max_c

                # Filter rule: True weather cells are highly saturated neon colors (S > 0.55)
                is_rain = (s > 0.55) and (v > 0.45)

                # Catch fallback values for deeper red convective cores
                if r > 140 and g < 40 and b < 80:
                    is_rain = True
                    
                # Skip the bottom-right legend box area to keep layout clean
                if x > (width - 250) and y > (height - 60):
                    is_rain = False

                if is_rain:
                    new_pixels[x, y] = (0, 0, 0)      # Solid black for rain
                else:
                    new_pixels[x, y] = (255, 255, 255)  # Pure white background

        new_img.save(image_path, "PNG")
        print("Success: High-contrast rain cells isolated perfectly.")
    except Exception as e:
        print(f"Error during image optimization: {e}")

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
                    print(f"Verified Radar Map downloaded: {latest_filename}")
                    
                    # Run clean HSV image isolation filter
                    process_radar_image(local_image_filename)
                    
    except Exception as e:
        print(f"Radar tracking failed: {e}")

    # ==========================================
    # 2. RUN LIVE 7-DAY FORECAST MATRIX PROCESSING
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
        print("Querying multi-day forecast grid variables for Budapest Central Coordinates...")
        api_url = "https://api.open-meteo.com/v1/forecast?latitude=47.4979&longitude=19.0402&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code&timezone=Europe/Budapest"
        
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            payload = response.json()
            daily = payload.get("daily", {})
            
            # Map structural arrays cleanly into your schema blocks
            for i in range(len(daily.get("time", []))):
                day_entry = {
                    "date_label": daily["time"][i],
                    "temp_max": f"{round(daily['temperature_2m_max'][i])}°C",
                    "temp_min": f"{round(daily['temperature_2m_min'][i])}°C",
                    "wind_speed_max": f"{round(daily['wind_speed_10m_max'][i])} km/h",
                    "cloud_icon_index": str(daily["weather_code"][i]),
                    "precipitation_mm": f"{daily['precipitation_sum'][i]} mm"
                }
                weather_data["budapest_forecast"].append(day_entry)
            print(f"Successfully compiled {len(weather_data['budapest_forecast'])} forecast entries.")
        else:
            print(f"API route returned status: {response.status_code}")
            
    except Exception as e:
        print(f"Failed pulling clean forecast schema: {e}")

    # ==========================================
    # 3. EXPORT NATIVE JSON ASSET
    # ==========================================
    with open("weather_data.json", "w", encoding="utf-8") as f:
        json.dump(weather_data, f, ensure_ascii=False, indent=2)
    print("Success! Native object array written to weather_data.json.")

if __name__ == "__main__":
    main()
