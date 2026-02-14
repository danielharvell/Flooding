# Flooding Visualization Project

A 3D globe-based flooding visualization using CesiumJS that allows users to simulate water level changes and see affected areas at any elevation from the Mariana Trench (-37,417 ft) to Mount Everest (+30,032 ft).

## Project Status

**Current Phase:** Proof-of-concept with Cesium World Terrain (land-only)  
**Next Phase:** Integrate GEBCO bathymetry data for ocean floor visualization

## Features

- ✅ 3D globe with satellite imagery (Bing Maps)
- ✅ Terrain-based flooding visualization using custom GLSL shaders
- ✅ Water level slider (-12,000 ft to +10,000 ft)
- ✅ Real-time terrain elevation display at center of view
- ✅ Works at all zoom levels (global to local)
- ✅ Automated testing with Playwright
- ⏳ Bathymetry (ocean floor) - pending GEBCO integration

## Quick Start

```bash
# Start local server
cd Flooding
python -m http.server 8000

# Open in browser
http://localhost:8000/flooding.html
```

## Architecture

### Core Files

| File | Description |
|------|-------------|
| `flooding.html` | Main application with CesiumJS viewer and ElevationRamp shader |
| `automated_test.py` | Playwright-based automated testing (elevation + zoom tests) |
| `analyze_screenshots.py` | Screenshot analysis for automated verification |
| `start.bat` | Windows batch file to start local server |

### ElevationRamp Material Shader

The flooding effect uses a custom GLSL shader that:
1. Samples terrain height at each fragment using `czm_sampleHeight()`
2. Compares height to user-controlled water level
3. Renders blue water overlay where terrain is below water level

```glsl
if (height < u_waterLevel) {
    // Below water - show blue water
    material.diffuse = vec3(0.0, 0.3, 0.8);
    material.alpha = 0.7;
} else {
    // Above water - transparent
    material.alpha = 0.0;
}
```

## Bathymetry Research & Decisions

### Why GEBCO (Chosen)

| Criteria | GEBCO 2025 | Cesium World Bathymetry |
|----------|------------|-------------------------|
| **Cost** | FREE (public domain) | $99/mo or $999/yr |
| **Resolution** | 15 arc-second (~450m) | Up to 1m in high-detail areas |
| **Data Sources** | GEBCO 2025 Grid | GEBCO 2023 + high-res data |
| **Integration** | Requires conversion | Seamless with CesiumJS |
| **Coverage** | Global (land + ocean) | Global (land + ocean) |

**Decision:** Use GEBCO due to cost constraints, with architecture designed for easy upgrade to Cesium ion in the future.

### GEBCO Resolution by Use Case

| Use Case | GEBCO (~450m) | Notes |
|----------|---------------|-------|
| Global flooding overview | ✅ Excellent | Perfect for visualization |
| Regional sea level rise | ✅ Good | Sufficient detail |
| Harbor/port analysis | ⚠️ Limited | May miss small features |
| UUV navigation | ❌ Insufficient | Needs Cesium ion resolution |
| Submarine simulation | ❌ Insufficient | Needs Cesium ion resolution |

### Cesium World Bathymetry Sources

Based on Cesium's documentation, their bathymetry includes:
- **GEBCO_2023 Grid** - Global 15 arc-second base layer
- **Great Barrier Reef** - 30m high-resolution data
- **swissBATHY3D** - Swiss lake bathymetry (1-3m)
- **NOAA CRMs** - US coastal relief models (3-10m)
- **Northern Gulf of Mexico** - 12m seismic-derived bathymetry

The high-resolution sources are what you pay for with Cesium ion subscription.

## Future Upgrade Path

### Minimizing GEBCO → Cesium ion Switch Effort

The codebase is designed to make switching terrain providers simple:

```javascript
// Current: GEBCO terrain (to be implemented)
const terrain = await Cesium.CesiumTerrainProvider.fromUrl('/terrain/gebco');

// Future: Cesium ion bathymetry (one line change)
const terrain = await Cesium.CesiumTerrainProvider.fromIonAssetId(2426648);
```

**Recommendation:** Create a config file to control terrain source:

```javascript
// config.js
export const TERRAIN_CONFIG = {
    source: 'gebco',  // Change to 'cesium_ion' when upgrading
    gebco_url: '/terrain/gebco',
    cesium_ion_asset_id: 2426648
};
```

## Testing

### Test Modes

1. **ELEVATION mode**: Tests water level response at Denver, CO (terrain: 5140 ft)
2. **ZOOM mode**: Tests visualization at 5 zoom levels from global to local

### Verified Results

| Location | Camera Height | Water Level Test | Result |
|----------|---------------|------------------|--------|
| Denver, CO | 50,000m | Below terrain (5000ft) | 0% blue ✅ |
| Denver, CO | 50,000m | Above terrain (5200ft) | 70%+ blue ✅ |
| Global view | 20,000,000m | 0-1000ft | 0% blue ✅ |
| Global view | 20,000,000m | 3000ft | 94.6% blue ✅ |
| Gulf Coast | 1,000,000m | 0-500ft | 86-100% blue ✅ |

### Running Tests

```bash
# Run automated tests
python automated_test.py

# Analyze screenshots
python analyze_screenshots.py
```

## Known Limitations

1. **No ocean floor detail** - Current implementation uses Cesium World Terrain (land only)
2. **Requires Cesium ion token** - Stored in `.cesium_token` file
3. **Performance on mobile** - Untested, may need optimization

## Next Steps

1. [ ] Convert GEBCO 2025 Grid to Cesium terrain format
2. [ ] Host converted terrain tiles locally or on cloud storage
3. [ ] Integrate GEBCO terrain with flooding visualization
4. [ ] Consider migrating to React/Vue for better state management
5. [ ] Add UI improvements (location search, presets, etc.)

## License

MIT License - See LICENSE file for details

