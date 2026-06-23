import os
import requests
from bs4 import BeautifulSoup

def main():
    url = "https://met.hu"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 1. Fetch the met.hu website source
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch page: {response.status_code}")
        return

    # 2. Find the radar image wrapper
    soup = BeautifulSoup(response.text, 'html.parser')
    img_tag = soup.find('img', {'class': 'radar-image'}) or soup.find('img', {'id': 'radar-image'})
    
    # Fallback to look for the known Hungarian radar composite asset name if structural class misses
    if not img_tag:
        img_tags = soup.find_all('img')
        for tag in img_tags:
            if 'rccmax' in tag.get('src', ''):
                img_tag = tag
                break

    if not img_tag or 'src' not in img_tag.attrs:
        print("Could not find the radar image element on the page.")
        return

    img_url = img_tag['src']
    if not img_url.startswith("http"):
        img_url = "https://met.hu" + img_url

    # 3. Download the raw radar image file
    print(f"Downloading latest frame from: {img_url}")
    img_data = requests.get(img_url).content

    # 4. Save it locally as a static filename
    with open("latest_radar.png", "wb") as f:
        f.write(img_data)
    print("Successfully saved latest_radar.png")

if __name__ == "__main__":
    main()

