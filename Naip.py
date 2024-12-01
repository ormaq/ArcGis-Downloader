import tkinter as tk
from tkinter import messagebox
import threading
import math
import os
import requests
from PIL import Image
from pyproj import Transformer
import json

def start_download():
    # Read the inputs from the GUI
    rest_server_link = rest_server_link_entry.get().strip()
    upper_left_lon = upper_left_lon_entry.get().strip()
    upper_left_lat = upper_left_lat_entry.get().strip()
    lower_right_lon = lower_right_lon_entry.get().strip()
    lower_right_lat = lower_right_lat_entry.get().strip()
    desired_resolution_input = desired_resolution_entry.get().strip()

    # Validate the inputs
    if not rest_server_link:
        messagebox.showerror("Input Error", "Please enter the REST server link.")
        return
    if not upper_left_lon or not upper_left_lat or not lower_right_lon or not lower_right_lat:
        messagebox.showerror("Input Error", "Please enter all AOI coordinates.")
        return
    if not desired_resolution_input:
        messagebox.showerror("Input Error", "Please enter the desired resolution.")
        return
    try:
        upper_left_lon = float(upper_left_lon)
        upper_left_lat = float(upper_left_lat)
        lower_right_lon = float(lower_right_lon)
        lower_right_lat = float(lower_right_lat)
        desired_resolution = float(desired_resolution_input)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numeric values.")
        return

    # Disable the Start Download button to prevent multiple clicks
    start_button.config(state=tk.DISABLED)

    # Start the download in a new thread
    download_thread = threading.Thread(
        target=download_tiles,
        args=(rest_server_link, upper_left_lon, upper_left_lat, lower_right_lon, lower_right_lat, desired_resolution),
        daemon=True  # Daemon thread will close when main program exits
    )
    download_thread.start()

def download_tiles(rest_server_link, upper_left_lon, upper_left_lat, lower_right_lon, lower_right_lat, desired_resolution):
    try:
        # Ensure the rest_server_link does not end with '/tile' or other extra path
        if rest_server_link.endswith('/tile'):
            rest_server_link = rest_server_link[:-5]
        if rest_server_link.endswith('/'):
            rest_server_link = rest_server_link[:-1]

        # Get tile info from the server
        service_url = f"{rest_server_link}?f=pjson"
        response = requests.get(service_url)
        response.raise_for_status()
        service_info = response.json()

        # Extract tile info
        if 'tileInfo' not in service_info:
            raise Exception("The service does not provide tileInfo.")

        tile_info = service_info['tileInfo']
        origin_x = tile_info['origin']['x']
        origin_y = tile_info['origin']['y']
        tile_size = tile_info['cols']  # Usually 256
        lods = tile_info['lods']
        spatial_ref = tile_info['spatialReference']
        wkid = spatial_ref.get('latestWkid', spatial_ref.get('wkid'))

        # Convert AOI coordinates to the server's spatial reference
        source_crs = "EPSG:4326"  # WGS84
        target_crs = f"EPSG:{wkid}"  # Server's spatial reference
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

        xmin, ymax = transformer.transform(upper_left_lon, upper_left_lat)
        xmax, ymin = transformer.transform(lower_right_lon, lower_right_lat)

        # Find the LOD with the closest resolution to the desired resolution
        desired_resolution = float(desired_resolution)
        closest_lod = min(lods, key=lambda lod: abs(lod['resolution'] - desired_resolution))
        resolution = closest_lod['resolution']
        level = closest_lod['level']

        # Update the GUI to inform the user of the selected LOD and resolution
        root.after(0, lambda: messagebox.showinfo("LOD Selected", f"Selected Level of Detail (LOD): {level}\nResolution: {resolution} meters per pixel"))

        # Calculate tile indices
        def lonlat_to_tile(x, y, resolution, origin_x, origin_y, tile_size):
            col = int((x - origin_x) / (resolution * tile_size))
            row = int((origin_y - y) / (resolution * tile_size))
            return col, row

        col_min, row_max = lonlat_to_tile(xmin, ymin, resolution, origin_x, origin_y, tile_size)
        col_max, row_min = lonlat_to_tile(xmax, ymax, resolution, origin_x, origin_y, tile_size)

        # Ensure min <= max
        col_min, col_max = min(col_min, col_max), max(col_min, col_max)
        row_min, row_max = min(row_min, row_max), max(row_min, row_max)

        # Inform the user of the number of tiles to download
        num_cols = col_max - col_min + 1
        num_rows = row_max - row_min + 1
        total_tiles = num_cols * num_rows
        root.after(0, lambda: messagebox.showinfo("Download Info", f"Number of tiles to download: {total_tiles}"))

        # Create directory to store tiles
        tiles_dir = 'tiles'
        if not os.path.exists(tiles_dir):
            os.makedirs(tiles_dir)

        # Download tiles
        tile_base_url = f"{rest_server_link}/tile"

        # Initialize variables for stitching
        stitched_width = num_cols * tile_size
        stitched_height = num_rows * tile_size
        stitched_image = Image.new('RGBA', (stitched_width, stitched_height))

        # Start downloading tiles
        for col in range(col_min, col_max + 1):
            for row in range(row_min, row_max + 1):
                tile_url = f"{tile_base_url}/{level}/{row}/{col}"
                tile_filename = os.path.join(tiles_dir, f"tile_{level}_{col}_{row}.png")
                try:
                    response = requests.get(tile_url)
                    response.raise_for_status()
                    with open(tile_filename, 'wb') as file:
                        file.write(response.content)
                    print(f"Downloaded {tile_filename}")
                    # Paste tile into stitched image
                    tile_image = Image.open(tile_filename)
                    x_offset = (col - col_min) * tile_size
                    y_offset = (row - row_min) * tile_size
                    stitched_image.paste(tile_image, (x_offset, y_offset))
                except Exception as e:
                    error_message = str(e)  # Capture the error message
                    root.after(0, lambda msg=error_message: messagebox.showerror("Error", f"An error occurred: {msg}"))


        # Save the stitched image
        stitched_image.save('stitched_image_full.png')
        print("Stitched image saved as 'stitched_image_full.png'")

        # Crop the stitched image to the exact AOI
        def calculate_pixel_offset(x, y, origin_x, origin_y, resolution, tile_size, col_min, row_min):
            col = (x - origin_x) / (resolution * tile_size)
            row = (origin_y - y) / (resolution * tile_size)
            pixel_x = (col - col_min) * tile_size
            pixel_y = (row - row_min) * tile_size
            return int(pixel_x), int(pixel_y)

        # Upper-left corner
        ul_pixel_x, ul_pixel_y = calculate_pixel_offset(xmin, ymax, origin_x, origin_y, resolution, tile_size, col_min, row_min)
        # Lower-right corner
        lr_pixel_x, lr_pixel_y = calculate_pixel_offset(xmax, ymin, origin_x, origin_y, resolution, tile_size, col_min, row_min)

        # Ensure coordinates are within image bounds
        ul_pixel_x = max(0, ul_pixel_x)
        ul_pixel_y = max(0, ul_pixel_y)
        lr_pixel_x = min(stitched_width, lr_pixel_x)
        lr_pixel_y = min(stitched_height, lr_pixel_y)

        # Crop the image
        cropped_image = stitched_image.crop((ul_pixel_x, ul_pixel_y, lr_pixel_x, lr_pixel_y))
        cropped_image.save('cropped_image.png')
        print("Cropped image saved as 'cropped_image.png'")

        # Inform the user that the download is complete
        root.after(0, lambda: messagebox.showinfo("Download Complete", "The images have been downloaded and stitched successfully."))

    except Exception as e:
        error_message = str(e)  # Capture the error message
        root.after(0, lambda msg=error_message: messagebox.showerror("Error", f"An error occurred: {msg}"))

    finally:
        # Re-enable the Start Download button
        root.after(0, lambda: start_button.config(state=tk.NORMAL))

# Create the GUI
root = tk.Tk()
root.title("ArcGIS Imagery Downloader")

# Set up the grid layout
for i in range(5):
    root.grid_rowconfigure(i, weight=1)
for i in range(4):
    root.grid_columnconfigure(i, weight=1)

# Create labels and entries
tk.Label(root, text="REST Server Link:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
rest_server_link_entry = tk.Entry(root, width=50)
rest_server_link_entry.grid(row=0, column=1, columnspan=3, sticky=tk.W, padx=5, pady=5)

tk.Label(root, text="Upper Left Longitude:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
upper_left_lon_entry = tk.Entry(root)
upper_left_lon_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

tk.Label(root, text="Upper Left Latitude:").grid(row=1, column=2, sticky=tk.E, padx=5, pady=5)
upper_left_lat_entry = tk.Entry(root)
upper_left_lat_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)

tk.Label(root, text="Lower Right Longitude:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
lower_right_lon_entry = tk.Entry(root)
lower_right_lon_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

tk.Label(root, text="Lower Right Latitude:").grid(row=2, column=2, sticky=tk.E, padx=5, pady=5)
lower_right_lat_entry = tk.Entry(root)
lower_right_lat_entry.grid(row=2, column=3, sticky=tk.W, padx=5, pady=5)

tk.Label(root, text="Desired Resolution (meters):").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
desired_resolution_entry = tk.Entry(root)
desired_resolution_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
desired_resolution_entry.insert(0, "0.1")  # Default value

# Start Download button
start_button = tk.Button(root, text="Start Download", command=start_download)
start_button.grid(row=4, column=1, columnspan=2, pady=10)

root.mainloop()
