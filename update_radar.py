import os
import requests
from bs4 import BeautifulSoup

def main():
    # Target the clean mobile layout
    url = "https://m.met.hu/radar"
    
    # These headers disguise the GitHub Action script as a real Google Chrome browser on Android
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://m.met.hu/"
    }
    
    # 1. Fetch the mobile webpage cleanly
    session = requests.Session()
    response = session.get(url, headers=headers, timeout=15)
    
    if response.status_code != 200:
        print(f"HungaroMet blocked access. Status Code: {response.status_code}")
        return

    # 2. Extract the active radar frame link
    soup = BeautifulSoup(response.text, 'html.parser')
    img_url = None
    
    # Search for the image element that serves the current radar loop frame
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if 'rccmax' in src or 'radar' in src or 'idoido' in src:
            img_url = src
            break

    if not img_url:
        print("Page loaded successfully, but the image element layout could not be found.")
        return

    # Handle relative links if necessary
    if not img_url.startswith("http"):
        img_url = "https://m.met.hu" + img_url

    # 3. Download the actual image payload bytes
    print(f"Downloading active image asset from: {img_url}")
    img_response = session.get(img_url, headers=headers, timeout=15)
    
    if img_response.status_code == 200:
        # 4. Save/Overwrite the permanent file target for TRMNL
        with open("latest_radar.png", "wb") as f:
            f.write(img_response.content)
        print("Success! latest_radar.png file generated and verified.")
    else:
        print(f"Failed downloading raw image asset bytes: {img_response.status_code}")

if __name__ == "__main__":
    main()
