from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import Toplevel
from screeninfo import get_monitors
import threading

def draw_number(draw, position, number, size, color):
    """Draw numbers with lines."""
    x, y = position
    line_width = size // 10
    
    if number == 1:
        draw.line([(x + size // 2, y), (x + size // 2, y + size)], fill=color, width=line_width)
    elif number == 2:
        draw.line([(x, y), (x + size, y)], fill=color, width=line_width)  # Top
        draw.line([(x + size, y), (x + size, y + size // 2)], fill=color, width=line_width)  # Right
        draw.line([(x, y + size // 2), (x + size, y + size // 2)], fill=color, width=line_width)  # Middle
        draw.line([(x, y + size // 2), (x, y + size)], fill=color, width=line_width)  # Left
        draw.line([(x, y + size), (x + size, y + size)], fill=color, width=line_width)  # Bottom
    elif number == 3:
        draw.line([(x, y), (x + size, y)], fill=color, width=line_width)  # Top
        draw.line([(x, y + size // 2), (x + size, y + size // 2)], fill=color, width=line_width)  # Middle
        draw.line([(x, y + size), (x + size, y + size)], fill=color, width=line_width)  # Bottom
    elif number == 4:
        draw.line([(x + size, y), (x + size, y + size)], fill=color, width=line_width)  # Right
        draw.line([(x, y + size // 2), (x + size, y + size // 2)], fill=color, width=line_width)  # Middle
        draw.line([(x, y), (x, y + size // 2)], fill=color, width=line_width)  # Left
    elif number == 5:
        draw.line([(x, y), (x + size, y)], fill=color, width=line_width)  # Top
        draw.line([(x, y), (x, y + size // 2)], fill=color, width=line_width)  # Left
        draw.line([(x, y + size // 2), (x + size, y + size // 2)], fill=color, width=line_width)  # Middle
        draw.line([(x, y + size), (x + size, y + size)], fill=color, width=line_width)  # Bottom
    elif number == 6:
        draw.line([(x, y + size // 2), (x + size, y + size // 2)], fill=color, width=line_width)  # Middle
        draw.line([(x, y), (x, y + size)], fill=color, width=line_width)  # Left
        draw.line([(x, y + size), (x + size, y + size)], fill=color, width=line_width)  # Bottom
        draw.line([(x, y + size // 2), (x + size, y + size // 2)], fill=color, width=line_width)  # Diagonal

def draw_smiley_face(draw, center, radius, color):
    """Draw a smiley face at the specified center with the given radius."""
    x, y = center
    # Draw the face outline
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], outline=color, width=3)
    # Draw the eyes
    eye_radius = radius // 6
    left_eye_center = (x - radius // 3, y - radius // 3)
    right_eye_center = (x + radius // 3, y - radius // 3)
    draw.ellipse([left_eye_center[0] - eye_radius, left_eye_center[1] - eye_radius,
                   left_eye_center[0] + eye_radius, left_eye_center[1] + eye_radius], 
                  fill=color)
    draw.ellipse([right_eye_center[0] - eye_radius, right_eye_center[1] - eye_radius,
                   right_eye_center[0] + eye_radius, right_eye_center[1] + eye_radius], 
                  fill=color)
    # Draw the mouth
    mouth_start = (x - radius // 2, y + radius // 4)
    mouth_end = (x + radius // 2, y + radius // 4)
    draw.arc([mouth_start[0], mouth_start[1] - 10, mouth_end[0], mouth_end[1] + 10],
              start=0, end=180, fill=color, width=3)

def create_custom_registration_image(width, height, line_color, fill_color):
    # Create a new image with a black background
    img = Image.new('RGB', (width, height), 'black')
    draw = ImageDraw.Draw(img)

    # Define properties
    large_font_size = 550  # Adjusted "F" size
    number_font_size = 200
    chessboard_size = 8
    chessboard_cell_size = 50
    circle_center = (width // 2, height // 2)
    circle_radius = min(width, height) // 4
    cross_size = 250
    gradient_bar_width = 200
    circle_thickness = 9  # Increased thickness for concentric circles
    cross_thickness = 60  # Increased thickness for cross
    f_thickness = 50      # Increased thickness for "F"

    # Draw the big "F" letter in the center
    x, y = width // 2 - large_font_size // 2, height // 2 - large_font_size // 2
    line_width = f_thickness
    draw.line([(x, y), (x + large_font_size * 0.8, y)], fill=line_color, width=line_width)  # Top horizontal
    draw.line([(x, y), (x, y + large_font_size * 0.6)], fill=line_color, width=line_width)  # Vertical part
    draw.line([(x, y + large_font_size * 0.4), (x + large_font_size * 0.6, y + large_font_size * 0.4)], fill=line_color, width=line_width)  # Middle horizontal

    # Draw numbers 1-6 with lines, slightly closer to the center
    number_positions = [
        (width // 4 - number_font_size // 2, height // 4 - number_font_size // 2),
        (3 * width // 4 - number_font_size // 2, height // 4 - number_font_size // 2),
        (width // 4 - number_font_size // 2, 3 * height // 4 - number_font_size // 2),
        (3 * width // 4 - number_font_size // 2, 3 * height // 4 - number_font_size // 2),
        (width // 4 - number_font_size // 2, height // 2 - number_font_size // 2),
        (3 * width // 4 - number_font_size // 2, height // 2 - number_font_size // 2),
    ]
    for number, pos in zip(range(1, 7), number_positions):
        draw_number(draw, pos, number, number_font_size, line_color)

    # Draw a black and white gradient bar pattern on the left side
    for i in range(gradient_bar_width):
        color = (i * 255 // gradient_bar_width, i * 255 // gradient_bar_width, 
                 i * 255 // gradient_bar_width)  # Grayscale gradient
        draw.line([(i, 0), (i, height)], fill=color, width=1)

    # Draw concentric circles in the top-right corner
    for i in range(5):
        draw.ellipse([(width - circle_radius - i * 20, i * 20),
                      (width - i * 20, circle_radius + i * 20)],
                     outline=line_color, width=circle_thickness)

    # Draw a small chessboard pattern in the bottom center
    chessboard_start_x = (width - chessboard_size * chessboard_cell_size) // 2
    chessboard_start_y = height - chessboard_size * chessboard_cell_size
    for i in range(chessboard_size):
        for j in range(chessboard_size):
            top_left = (chessboard_start_x + i * chessboard_cell_size, 
                        chessboard_start_y + j * chessboard_cell_size)
            bottom_right = (chessboard_start_x + (i + 1) * chessboard_cell_size, 
                            chessboard_start_y + (j + 1) * chessboard_cell_size)
            fill = fill_color if (i + j) % 2 == 0 else 'black'
            draw.rectangle([top_left, bottom_right], fill=fill)

    # Draw a thick cross shape in the top-left corner
    cross_center = (cross_size, cross_size)
    draw.line([(cross_center[0] - cross_size, cross_center[1]), 
               (cross_center[0] + cross_size, cross_center[1])], 
              fill=line_color, width=cross_thickness)
    draw.line([(cross_center[0], cross_center[1] - cross_size), 
               (cross_center[0], cross_center[1] + cross_size)], 
              fill=line_color, width=cross_thickness)

    # Draw a smiley face in the bottom-right corner
    smiley_center = (width - 900, height - 700)
    smiley_radius = 50
    draw_smiley_face(draw, smiley_center, smiley_radius, line_color)
    
      # Draw a smiley face in the bottom-right corner
    smiley_center = (width - 1000, height - 950)
    smiley_radius = 100
    draw_smiley_face(draw, smiley_center, smiley_radius, line_color)
    return img

# def show_image_fullscreen_on_second_monitor(image_path):
#     """Open the image on the second monitor in full screen mode."""
#     # Get monitor information
#     monitors = get_monitors()
#     if len(monitors) < 2:
#         raise RuntimeError("Second monitor not detected.")
    
#     # Get the dimensions of the second monitor
#     second_monitor = monitors[1]
#     x, y, width, height = second_monitor.x, second_monitor.y, second_monitor.width, second_monitor.height

#     # Initialize the Tkinter window
#     root = tk.Tk()
#     root.withdraw()  # Hide the main window
    
#     # Create a new top-level window
#     top = Toplevel(root)
#     top.geometry(f"{width}x{height}+{x}+{y}")  # Set the geometry to match the second monitor
#     top.attributes('-fullscreen', True)
#     top.attributes('-topmost', True)  # Keep on top
#     top.bind("<Escape>", lambda e: top.destroy())  # Bind escape key to exit full screen

#     # Load and display the image
#     img = Image.open(image_path)
#     fig, ax = plt.subplots()
#     ax.imshow(img)
#     ax.axis('off')  # Hide axes

#     # Use matplotlib's FigureCanvasTkAgg to display the image
#     canvas = FigureCanvasTkAgg(fig, master=top)
#     canvas.draw()

#     # Embed the canvas into the Tkinter top-level window
#     canvas.get_tk_widget().pack(fill='both', expand=True)

#     root.mainloop()

def show_image_fullscreen_on_second_monitor(image_path):
    """Open the image on the second monitor in full screen mode."""

    def show_image():
        # Get monitor information
        monitors = get_monitors()
        if len(monitors) < 2:
            raise RuntimeError("Second monitor not detected.")
        
        # Get the dimensions of the second monitor
        second_monitor = monitors[0]
        x, y, width, height = second_monitor.x, second_monitor.y, second_monitor.width, second_monitor.height

        # Initialize the Tkinter window
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Create a new top-level window
        top = Toplevel(root)
        top.geometry(f"{width}x{height}+{x}+{y}")  # Set the geometry to match the second monitor
        top.attributes('-fullscreen', True)
        top.attributes('-topmost', True)  # Keep on top
        top.bind("<Escape>", lambda e: top.destroy())  # Bind escape key to exit full screen

        # Load and display the image
        img2 = Image.open(image_path)
        fig, ax = plt.subplots()
        ax.imshow(img2)
        ax.axis('off')  # Hide axes

        # Use matplotlib's FigureCanvasTkAgg to display the image
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()

        # Embed the canvas into the Tkinter top-level window
        canvas.get_tk_widget().pack(fill='both', expand=True)

        root.mainloop()

    # Start the Tkinter event loop in a separate thread
    thread = threading.Thread(target=show_image)
    thread.start()
    
# Example usage
image_path = 'custom_registration_image.png'  # Your image file path
img = Image.open(image_path)
width, height = img.size
line_color = 'white'  # Color for lines and outlines
fill_color = 'white'   # Color for chessboard fill
custom_image = create_custom_registration_image(width, height, line_color, fill_color)
custom_image.save(image_path)  # Save the image
show_image_fullscreen_on_second_monitor(image_path)  # Open image in full-screen on second monitor