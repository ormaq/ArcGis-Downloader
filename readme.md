# ArcGIS Imagery Downloader

## Requirements

Make sure you have the following Python libraries installed:

- `tkinter` (included with Python standard library)
- `requests`
- `Pillow`
- `pyproj`

You can install the required libraries using pip:

`pip install requests Pillow pyproj`

## How to Use

1. **Run the Program**: Run the Python script using:
   `python script_name.py`
   Replace `script_name.py` with the filename of the script.

2. **Enter Inputs in the GUI**:
   - **REST Server Link**: The base URL of the ArcGIS REST server (e.g., `https://yourserver.com/arcgis/rest/services/ServiceName/MapServer`).
   - **Upper Left Coordinates (Longitude and Latitude)**: The top-left corner of your AOI.
   - **Lower Right Coordinates (Longitude and Latitude)**: The bottom-right corner of your AOI.
   - **Desired Resolution (meters)**: The resolution in meters per pixel. Default is `0.1`.

3. **Start the Download**:
   - Click the "Start Download" button.
   - The program will fetch tiles, stitch them, and save the output images.

4. **Output Files**:
   - `stitched_image_full.png`: The full stitched image.
   - `cropped_image.png`: The cropped image matching the exact AOI.

## Troubleshooting

- Ensure the REST server supports tile services and provides `tileInfo` in its JSON response.
- Check your internet connection if tile downloads fail.
- Make sure the input coordinates are valid and in WGS84 (EPSG:4326) format.

## License

This program is free to use and modify.
