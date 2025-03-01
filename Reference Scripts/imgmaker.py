import cv2
import numpy as np
import matplotlib.pyplot as plt


# Define image resolution
width, height = 1936, 1096

# Create a blank grayscale image
image = np.zeros((height, width), dtype=np.uint8)

# Define the new positions for the shapes closer to the center
# Circle: Centered at 1/3rd width and 1/2 height
circle_center = (width // 3, height // 2)
circle_radius = 50

# Triangle: Centered at 3/4th width and 1/4th height
triangle_points = np.array([[width * 3 // 4 - 50, height // 4 - 50], 
                            [width * 3 // 4 + 50, height // 4 - 50], 
                            [width * 3 // 4, height // 4 + 50]])

# Rectangle: Centered at 1/4th width and 3/4th height
rectangle_top_left = (width // 4 - 50, height * 3 // 4 - 50)
rectangle_bottom_right = (width // 4 + 50, height * 3 // 4 + 50)

# Draw the white circle
cv2.circle(image, circle_center, circle_radius, (255), -1)

# Draw the white triangle
cv2.drawContours(image, [triangle_points], 0, (255), -1)

# Draw the white rectangle
cv2.rectangle(image, rectangle_top_left, rectangle_bottom_right, (255), -1)
# Define the smiley face position
smiley_center = (width // 2, height // 5)
smiley_radius = 80

# Draw the smiley face outline
cv2.circle(image, smiley_center, smiley_radius, (255), 5)

# Draw the eyes
eye_radius = 10
left_eye_center = (smiley_center[0] - 25, smiley_center[1] - 20)
right_eye_center = (smiley_center[0] + 25, smiley_center[1] - 20)
cv2.circle(image, left_eye_center, eye_radius, (255), -1)
cv2.circle(image, right_eye_center, eye_radius, (255), -1)

# Draw the mouth (a semi-circle)
mouth_center = (smiley_center[0], smiley_center[1] + 20)
mouth_axes = (30, 15)
cv2.ellipse(image, mouth_center, mouth_axes, 0, 0, 180, (255), 3)

# IMPORTANT: (USE the inverse H data )Define the homography matrix
homography_matrix = np.array([[ 1.03186264e+00, -7.64954812e-02, -3.43953305e+00],
 [ 1.07775756e-01,  1.44722667e+00, -2.94484718e+02],
 [-3.03464916e-05,  1.32547455e-05,  9.97876834e-01]])

# Save the image with drawings
#cv2.imwrite('custom_registration_image.png', image)

image = cv2.imread("custom_registration_image.png")
image = cv2.flip(image, 0) #the obtained homography matrix is for the flipped image

# Apply the homography matrix to the image
projected_image = cv2.warpPerspective(image, homography_matrix, (width, height))

# Save the image
#cv2.imwrite('testshapes_image_projected.png', projected_image)
cv2.imwrite('Homedcustom_registration_image.png', projected_image)

# Display the image
cv2.imshow(' Image', image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Display the image
cv2.imshow('Projected Image', projected_image)
cv2.waitKey(0)
cv2.destroyAllWindows()


# Compute the inverse homography matrix
inverse_homography = np.linalg.inv(homography_matrix)

img3 = cv2.imread("custom_registration_image.png")
img3 = cv2.flip(img3, 0)

# Warp img3 using the inverse homography matrix
height3, width3, _ = img3.shape
inverse_transformed_img3 = cv2.warpPerspective(img3, inverse_homography, (width3, height3))

#Let's try rotating the image counterclowise by 10 degrees
# Get the dimensions of the image
(h, w) = inverse_transformed_img3.shape[:2]
# Calculate the center of the image
center = (w // 2, h // 2)
# Create the rotation matrix for a 10 degree counterclockwise rotation
rotation_matrix = cv2.getRotationMatrix2D(center, 1, 1.0)

# Apply the rotation to the image
inverse_transformed_img3 = cv2.warpAffine(inverse_transformed_img3, rotation_matrix, (w, h))

# Flip the first image along the x-axis
#inverse_transformed_img3 = cv2.flip(inverse_transformed_img3, 0)

# Save the inverse transformed image
cv2.imwrite('ReverseHomedcustom_registration_image_output.jpg', inverse_transformed_img3)

# Plot img3 and the inverse transformed image
fig, axs = plt.subplots(1, 2, figsize=(12, 6))

# Plot img3
axs[0].imshow(cv2.cvtColor(img3, cv2.COLOR_BGR2RGB))
axs[0].set_title('On the sensor')
axs[0].axis('off')

# Plot the inverse transformed image
axs[1].imshow(cv2.cvtColor(inverse_transformed_img3, cv2.COLOR_BGR2RGB))
axs[1].set_title('On the DMD')
axs[1].axis('off')

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()
