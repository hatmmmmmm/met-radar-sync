def process_radar_image(image_path):
    """
    Compares pixel colors against the official HungaroMet radar dBZ color scale.
    Isolates precise radar returns while dropping the terrain map to pure white.
    """
    print("Processing radar image via exact color map scale matching...")
    try:
        if not os.path.exists(image_path):
            print(f"Error: Target image {image_path} does not exist.")
            return

        img = Image.open(image_path).convert("RGB")
        pixels = img.load()
        width, height = img.size

        new_img = Image.new("RGB", (width, height), (255, 255, 255))
        new_pixels = new_img.load()

        # The exact dominant RGB color targets found in HungaroMet's radar overlay scale:
        # Includes: Light blues, deep blues, cyans, vivid greens, bright yellows, orange, and reds.
        TARGET_RADAR_COLORS = [
            (0, 0, 160),     # Deep Blue
            (0, 90, 255),    # Light Blue
            (0, 180, 255),   # Cyan / Light Rain
            (0, 210, 140),   # Teal / Turquoise
            (0, 215, 0),     # Bright Green
            (0, 160, 0),     # Dark Green
            (170, 220, 0),   # Lime Green
            (255, 240, 0),   # Bright Yellow
            (255, 180, 0),   # Orange
            (255, 0, 0),     # Bright Red
            (180, 0, 0),     # Dark Red
            (160, 0, 160)    # Purple/Convective Core
        ]

        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]

                # Quick preliminary check: if it's completely grayscale/neutral terrain, skip it
                if abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10:
                    new_pixels[x, y] = (255, 255, 255)
                    continue

                is_rain = False
                # Measure the mathematical Euclidean distance to our valid color targets
                for tr, tg, tb in TARGET_RADAR_COLORS:
                    # Color space distance formula
                    color_distance = ((r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2) ** 0.5
                    
                    # If the color matches a radar color closely (within a distance threshold of 65)
                    if color_distance < 65:
                        is_rain = True
                        break

                # Clean up the bottom corner watermark branding elements if present
                if x < 60 and y > (height - 60):
                    is_rain = False
                if x > (width - 250) and y > (height - 60):
                    is_rain = False

                if is_rain:
                    new_pixels[x, y] = (0, 0, 0)      # Solid black rain storm cell
                else:
                    new_pixels[x, y] = (255, 255, 255)  # Pure clear background

        new_img.save(image_path, "PNG")
        print("Success: High-contrast rain matrix extracted successfully.")
    except Exception as e:
        print(f"Error during color map comparison step: {e}")
