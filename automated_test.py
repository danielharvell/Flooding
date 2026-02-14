"""
Automated Browser Testing for Flooding Visualization
Uses Playwright to control the browser and capture screenshots at various elevations.

Usage:
    python automated_test.py

Note: Requires CESIUM_TOKEN environment variable or will prompt for it.
"""

import os
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

# Configuration
BASE_URL = "http://localhost:8000/flooding.html"  # Python HTTP server

# Get Cesium token from file, environment variable, or prompt
def get_cesium_token():
    """Get Cesium token from various sources."""
    # Check environment variable first
    token = os.environ.get("CESIUM_TOKEN", None)
    if token:
        return token.strip()

    # Check for token file in current directory
    token_file = os.path.join(os.path.dirname(__file__), ".cesium_token")
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return f.read().strip()

    # Prompt user and save to file
    print("Cesium ion Access Token not found.")
    print("Get a free token at: https://ion.cesium.com/tokens")
    token = input("Enter your token (will be saved to .cesium_token): ").strip()

    if token:
        with open(token_file, 'w') as f:
            f.write(token)
        print(f"Token saved to {token_file}")

    return token
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "test_screenshots")
RESULTS_FILE = os.path.join(os.path.dirname(__file__), "test_results.json")

# Test mode: "ELEVATION" or "ZOOM"
TEST_MODE = "ZOOM"  # Change to "ELEVATION" for Denver elevation tests

# Test elevations in feet - Testing Denver, Colorado
# Terrain at center shows 5140 ft - test around that elevation
TEST_ELEVATIONS = [5000, 5050, 5100, 5120, 5130, 5140, 5150, 5160, 5180, 5200]

# Zoom level tests - camera heights in meters and water levels to test
# Tests flooding at various zoom levels from global to local
ZOOM_TESTS = [
    # (name, longitude, latitude, camera_height_m, water_levels_ft)
    ("Global_Full", 0, 20, 20000000, [0, 500, 1000, 3000]),  # Full globe view
    ("Global_Half", -40, 30, 10000000, [0, 500, 1000]),  # Half globe (Atlantic)
    ("Continental", -100, 40, 5000000, [0, 500, 1000]),  # North America
    ("Regional", -95, 30, 1000000, [0, 100, 500]),  # Gulf Coast
    ("Local_Coast", -90.1, 29.95, 50000, [0, 10, 50, 100]),  # New Orleans coast
]


async def wait_for_cesium_ready(page, timeout=60000):
    """Wait for Cesium to be fully loaded."""
    print("Waiting for Cesium to load...")

    # First wait for basic page load
    await page.wait_for_load_state("domcontentloaded")
    print("  DOM content loaded")

    # Take a debug screenshot to see what's on the page
    debug_screenshot = os.path.join(SCREENSHOT_DIR, "debug_initial.png")
    await page.screenshot(path=debug_screenshot)
    print(f"  Debug screenshot saved: {debug_screenshot}")

    # Check page content
    page_title = await page.title()
    print(f"  Page title: {page_title}")

    # Try to wait for slider
    try:
        await page.wait_for_selector("#heightSlider", timeout=timeout)
        print("  Slider found!")
    except Exception as e:
        print(f"  Warning: Slider not found: {e}")
        # Take another screenshot
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "debug_no_slider.png"))
        raise

    # Wait for terrain to load by checking for debug info updates
    print("Waiting for terrain to load...")
    await page.wait_for_timeout(10000)  # 10 second wait for terrain

    if TEST_MODE == "ELEVATION":
        # Move camera to Denver, Colorado - the "Mile High City" at ~5,280 ft elevation
        print("Moving camera to Denver, Colorado...")
        await page.evaluate("""
            viewer.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(-104.99, 39.74, 15000),
                orientation: {
                    heading: Cesium.Math.toRadians(0),
                    pitch: Cesium.Math.toRadians(-70),
                    roll: 0
                }
            });
        """)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "debug_denver_view.png"))
    else:
        # For ZOOM mode, start at global view
        print("Setting up global view...")
        await page.evaluate("""
            viewer.camera.setView({
                destination: Cesium.Cartesian3.fromDegrees(0, 20, 20000000),
                orientation: {
                    heading: 0,
                    pitch: Cesium.Math.toRadians(-90),
                    roll: 0
                }
            });
        """)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=os.path.join(SCREENSHOT_DIR, "debug_global_view.png"))

    # Get initial terrain height to verify terrain is loading
    initial_debug = await get_debug_info(page)
    print(f"Initial debug info: {initial_debug}")
    print("Cesium should be ready now.")


async def set_elevation(page, elevation_ft):
    """Set the water level elevation using the slider."""
    await page.evaluate(f"""
        const slider = document.getElementById('heightSlider');
        // Temporarily set step to 1 to allow exact values
        slider.step = 1;
        slider.value = {elevation_ft};
        slider.dispatchEvent(new Event('input'));
        console.log('Slider set to:', slider.value, 'ft');
        console.log('Water level in meters:', {elevation_ft} * 0.3048);
    """)
    # Wait for material to update and terrain to re-render
    await page.wait_for_timeout(1500)


async def get_debug_info(page):
    """Get debug info displayed on the page."""
    try:
        return await page.locator("#debugInfo").text_content()
    except:
        return "Debug info not found"


async def get_current_height_label(page):
    """Get the current height label."""
    try:
        return await page.locator("#currentHeight").text_content()
    except:
        return "Unknown"


async def run_tests():
    """Run the full test suite."""
    # Get Cesium token first
    cesium_token = get_cesium_token()
    if not cesium_token:
        print("Error: No Cesium token provided. Exiting.")
        return

    # Create screenshot directory
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    results = {
        "timestamp": datetime.now().isoformat(),
        "test_elevations": TEST_ELEVATIONS,
        "screenshots": [],
    }

    print("Starting Playwright...")

    async with async_playwright() as p:
        # Launch browser (non-headless so we can see what's happening)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Capture console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: console_logs.append(f"ERROR: {exc}"))

        try:
            # First navigate to the page to set up origin for localStorage
            print(f"Setting up Cesium token...")
            await page.goto("http://localhost:8000/")

            # Set the Cesium token in localStorage
            await page.evaluate(f"""
                localStorage.setItem('cesiumIonAccessToken', '{cesium_token}');
            """)

            print(f"Navigating to {BASE_URL}...")
            await page.goto(BASE_URL)

            await wait_for_cesium_ready(page)

            if TEST_MODE == "ZOOM":
                # Run zoom level tests
                print(f"\n=== ZOOM LEVEL TESTS ({len(ZOOM_TESTS)} locations) ===")
                results["test_mode"] = "ZOOM"
                results["zoom_tests"] = ZOOM_TESTS

                for i, (name, lon, lat, cam_height, water_levels) in enumerate(ZOOM_TESTS):
                    print(f"\n[{i+1}/{len(ZOOM_TESTS)}] Testing: {name}")
                    print(f"  Camera: ({lat}, {lon}) at {cam_height:,}m")

                    # Move camera to this location
                    await page.evaluate(f"""
                        viewer.camera.setView({{
                            destination: Cesium.Cartesian3.fromDegrees({lon}, {lat}, {cam_height}),
                            orientation: {{
                                heading: 0,
                                pitch: Cesium.Math.toRadians(-90),
                                roll: 0
                            }}
                        }});
                    """)
                    await page.wait_for_timeout(5000)  # Wait for tiles to load

                    for water_level in water_levels:
                        print(f"    Water level: {water_level} ft")
                        await set_elevation(page, water_level)
                        await page.wait_for_timeout(2000)

                        filename = f"zoom_{name}_{water_level:+05d}ft.png"
                        filepath = os.path.join(SCREENSHOT_DIR, filename)
                        await page.screenshot(path=filepath)

                        debug_info = await get_debug_info(page)
                        results["screenshots"].append({
                            "test_name": name,
                            "location": {"lon": lon, "lat": lat},
                            "camera_height_m": cam_height,
                            "water_level_ft": water_level,
                            "screenshot": filename,
                            "debug_info": debug_info,
                        })
                        print(f"      Screenshot: {filename}")
            else:
                # Run elevation tests (original behavior)
                print(f"\nRunning tests for {len(TEST_ELEVATIONS)} elevation levels...")
                results["test_mode"] = "ELEVATION"

                for i, elevation in enumerate(TEST_ELEVATIONS):
                    print(f"  [{i+1}/{len(TEST_ELEVATIONS)}] Testing elevation: {elevation:+d} ft")

                    await set_elevation(page, elevation)
                    await page.wait_for_timeout(1000)

                    filename = f"elevation_{elevation:+06d}ft.png"
                    filepath = os.path.join(SCREENSHOT_DIR, filename)
                    await page.screenshot(path=filepath)

                    debug_info = await get_debug_info(page)
                    height_label = await get_current_height_label(page)

                    results["screenshots"].append({
                        "elevation_ft": elevation,
                        "screenshot": filename,
                        "debug_info": debug_info,
                        "height_label": height_label,
                    })

                    print(f"      Screenshot saved: {filename}")
                    print(f"      Debug: {debug_info}")

            # Add console logs to results
            results["console_logs"] = console_logs

            # Save results
            with open(RESULTS_FILE, 'w') as f:
                json.dump(results, f, indent=2)

            print(f"\n✓ Tests complete! Results saved to {RESULTS_FILE}")
            print(f"✓ Screenshots saved to {SCREENSHOT_DIR}")

            # Print relevant console logs
            print(f"\n--- Console Logs ({len(console_logs)} total) ---")
            for log in console_logs[:30]:  # First 30 logs
                print(f"  {log}")

        except Exception as e:
            print(f"\nError during testing: {e}")
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(run_tests())

