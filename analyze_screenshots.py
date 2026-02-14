"""
Analyze screenshots to detect flooding (blue color) presence.
This script examines the center region of each screenshot and measures blue color intensity.
"""

import os
from PIL import Image
import json

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "test_screenshots")

def analyze_image(filepath):
    """Analyze a screenshot for blue (flood) color at the center."""
    try:
        img = Image.open(filepath)
        width, height = img.size
        
        # Sample a region at the center (100x100 pixels)
        center_x, center_y = width // 2, height // 2
        box_size = 50
        
        # Count blue-ish pixels in the center region
        blue_pixels = 0
        total_pixels = 0
        avg_r, avg_g, avg_b = 0, 0, 0
        
        for x in range(center_x - box_size, center_x + box_size):
            for y in range(center_y - box_size, center_y + box_size):
                if 0 <= x < width and 0 <= y < height:
                    pixel = img.getpixel((x, y))
                    if len(pixel) >= 3:
                        r, g, b = pixel[0], pixel[1], pixel[2]
                        avg_r += r
                        avg_g += g
                        avg_b += b
                        total_pixels += 1
                        
                        # Detect blue flooding - blue should be higher than red/green
                        # and the pixel should have significant blue component
                        if b > 100 and b > r * 1.3 and b > g * 1.1:
                            blue_pixels += 1
        
        if total_pixels > 0:
            avg_r /= total_pixels
            avg_g /= total_pixels
            avg_b /= total_pixels
            blue_ratio = blue_pixels / total_pixels
        else:
            blue_ratio = 0
            
        return {
            "blue_pixels": blue_pixels,
            "total_pixels": total_pixels,
            "blue_ratio": round(blue_ratio, 4),
            "avg_color": (round(avg_r), round(avg_g), round(avg_b)),
            "has_flooding": blue_ratio > 0.1  # Consider flooded if >10% blue pixels
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    """Analyze all screenshots (zoom or elevation)."""

    # Check for zoom screenshots first
    zoom_files = sorted([f for f in os.listdir(SCREENSHOT_DIR) if f.startswith("zoom_")])

    if zoom_files:
        print(f"Analyzing {len(zoom_files)} ZOOM screenshots...\n")
        print(f"{'Test Name':<25} {'Water Level':>12} {'Blue Ratio':>10} {'Flooding?':>10}")
        print("-" * 65)

        results = []
        for filename in zoom_files:
            filepath = os.path.join(SCREENSHOT_DIR, filename)
            analysis = analyze_image(filepath)

            # Parse: zoom_Global_Full_+0000ft.png
            parts = filename.replace("zoom_", "").replace(".png", "").rsplit("_", 1)
            test_name = parts[0]
            water_level = int(parts[1].replace("ft", "").replace("+", ""))

            results.append({
                "test_name": test_name,
                "water_level_ft": water_level,
                **analysis
            })

            if "error" not in analysis:
                flooding = "YES" if analysis["has_flooding"] else "no"
                print(f"{test_name:<25} {water_level:>+10} ft {analysis['blue_ratio']:>10.1%} {flooding:>10}")
            else:
                print(f"{test_name:<25} {water_level:>+10} ft ERROR: {analysis['error']}")

        print("-" * 65)

        # Save analysis
        output_file = os.path.join(SCREENSHOT_DIR, "zoom_analysis.json")
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Zoom analysis saved to: {output_file}")
        return results

    # Fall back to elevation screenshots
    files = sorted([f for f in os.listdir(SCREENSHOT_DIR) if f.startswith("elevation_")])

    if not files:
        print("No screenshots found!")
        return {}

    results = {}
    print(f"Analyzing {len(files)} ELEVATION screenshots...\n")
    print(f"{'Elevation':<15} {'Blue Ratio':<12} {'Avg Color (R,G,B)':<20} {'Flooding?':<10}")
    print("-" * 60)

    for filename in files:
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        analysis = analyze_image(filepath)

        elev_str = filename.replace("elevation_", "").replace("ft.png", "")
        is_negative = elev_str.startswith("-")
        elev_num = elev_str.lstrip("+-").lstrip("0") or "0"
        elevation = int(elev_num) * (-1 if is_negative else 1)

        results[elevation] = analysis

        if "error" not in analysis:
            flooding = "YES" if analysis["has_flooding"] else "no"
            color = f"({analysis['avg_color'][0]}, {analysis['avg_color'][1]}, {analysis['avg_color'][2]})"
            print(f"{elevation:>10} ft    {analysis['blue_ratio']:<12.4f} {color:<20} {flooding:<10}")
        else:
            print(f"{elevation:>10} ft    ERROR: {analysis['error']}")

    print("-" * 60)

    output_file = os.path.join(SCREENSHOT_DIR, "analysis_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Analysis saved to: {output_file}")

    return results


if __name__ == "__main__":
    main()

