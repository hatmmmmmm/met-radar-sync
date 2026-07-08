import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from PIL import Image

def process_radar_image(image_path):
    """
    Strips away the background geography map and converts any 
    precipitation metrics into solid black shapes for clear 1-bit display visibility.
    """
    print("Processing radar image for high-contrast e-ink rendering...")
    try:
        # Open and ensure target is in a true 24-bit RGB space
        img = Image.open(image_path).convert("RGB")
        pixels = img.load()
        width, height = img.size

        # Construct a pure white frame asset
        new_img = Image.new("RGB", (width, height), (255, 255, 255))
        new_pixels = new_img.load()

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]

                # Isolate high-saturation radar elements (vibrant blues, greens, yellows, reds)
                # Terrain and map markings have low variations between R, G, and B lines
                max_val = max(r, g, b)
                min_val = min(r, g, b)
                delta = max_val - min_val
                
                # Filter rule: Actual weather overlays are vibrant (high delta)
                is_rain_cell = (delta > 25) and (max_val > 45)

                # Catch fallback values for deeper red convective cores
                if r > 130 and g < 60 and b < 60:
                    is_rain_cell = True

                if is_rain_cell:
                    new_pixels[x, y] = (0, 0, 0) # Render precipitation as solid black
                else:
                    new_pixels[x, y] = (255, 255, 255) # Wipe the terrain out to pure white

        new_img.save(image_path, "PNG")
        print("Success: High-contrast map override written.")
    except Exception as e:
        print(f"Error during image optimization layer manipulation: {e}")

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
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
                # FIXED: Corrected single index array selector syntax error
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
                    
                    # Process image modifications
                    process_radar_image(local_image_filename)
                    
    except Exception as e:
        print(f"Radar tracking failed: {e}")

    # ==========================================
    # 2. SCRAPE 7-DAY FORECAST FROM MET.HU MOBILE
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
        mobile_url = "https://m.met.hu/idojaras/telepules/budapest"
        print(f"Scraping official forecast from: {mobile_url}")
        page_resp = requests.get(mobile_url, headers=headers, timeout=15)
        
        if page_resp.status_code == 200:
            page_resp.encoding = 'utf-8'
            soup = BeautifulSoup(page_resp.text, 'html.parser')
            forecast_blocks = soup.find_all('div', class_='elorejelzes-nap')
            
            for block in forecast_blocks:
                date_el = block.find('div', class_='nap-fejlec')
                date_label = date_el.text.strip() if date_el else "N/A"
                
                temp_el = block.find('div', class_='nap-homerseklet')
                temp_text = temp_el.text.strip() if temp_el else "N/A / N/A"
                temps = [t.strip() for t in temp_text.split('/')]
                tmax = temps[0] if len(temps) > 0 else "N/A"
                tmin = temps[1] if len(temps) > 1 else "N/A"
                
                cond_img = block.find('img', class_='nap-ikon')
                icon_idx = "N/A"
                if cond_img and cond_img.get('src'):
                    icon_idx = cond_img.get('src').split('/')[-1].replace('.png', '')
                
                precip_el = block.find('div', class_='nap-csapadek')
                precip = precip_el.text.strip() if precip_el else "0 mm"

                wind_el = block.find('div', class_='nap-szel')
                wind = wind_el.text.strip() if wind_el else "N/A"

                day_entry = {
                    "date_label": date_label,
                    "temp_max": tmax,
                    "temp_min": tmin,
                    "cloud_icon_index": icon_idx,
                    "precipitation_mm": precip,
                    "wind_speed_max": wind
                }
                weather_data["budapest_forecast"].append(day_entry)
                
            print(f"Successfully processed {len(weather_data['budapest_forecast'])} forecast days.")
            
    except Exception as e:
        print(f"Failed parsing mobile layout: {e}")

    # ==========================================
    # 3. EXPORT NATIVE JSON ASSET
    # ==========================================
    with open("weather_data.json", "w", encoding="utf-8") as f:
        json.dump(weather_data, f, ensure_ascii=False, indent=2)
    print("Success! Native object array written to weather_data.json.")

if __name__ == "__main__":
    main()
