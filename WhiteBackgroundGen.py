from PIL import Image

# Run this to produce a White Background Image


# Define the resolution
width, height = 1936, 1096

# Create an image with the specified resolution and solid white color
white_color = (255, 255, 255)  # RGB for white
image = Image.new("RGB", (width, height), white_color)

# Save the image as a .png file
image.save("solid_white_image.png")

print("Image saved as solid_white_image.png")