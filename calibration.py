import cv2
import numpy as np
import matplotlib.pyplot as plt

def decompose_homography(H):
    # Ensure the matrix is normalized
    H = H / H[2, 2] #h_33

    # Extract translation
    tx = H[0, 2]
    ty = H[1, 2]

    # Extract rotation and scaling from the upper-left 2x2 part
    r1 = H[0, 0:2]
    r2 = H[1, 0:2]

    # Compute scaling factors
    sx = np.linalg.norm(r1)
    sy = np.linalg.norm(r2)

    # Normalize the rotation components
    r1 /= sx
    r2 /= sy

    # Construct the rotation matrix vertically
    R = np.vstack([r1, r2])

    # Compute the rotation angle
    angle = np.arctan2(r2[0], r2[1]) * (180 / np.pi)

    return tx, ty, sx, sy, angle

# Read images
img1 = cv2.imread("custom_registration_image.png")
img2 = cv2.imread("image_0.png")
img3 = cv2.imread("Synch5.png")

# Flip the first image along the x-axis
img1 = cv2.flip(img1, 0)

# Convert images to grayscale
img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

# Get the dimensions of the second image
height, width = img2_gray.shape

# Initialize SIFT detector
sift = cv2.SIFT_create()

# Find keypoints and descriptors
kp1, d1_image = sift.detectAndCompute(img1_gray, None)
kp2, d2_image = sift.detectAndCompute(img2_gray, None)

# Match descriptors
matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
matches = matcher.match(d1_image, d2_image)

# Sort matches by distance (best matches first)
matches = sorted(matches, key=lambda x: x.distance)
matches = matches[:int(len(matches) * 0.9)]

# Check if there are enough matches
if len(matches) < 4:
    print("Not enough matches found - at least 4 required")
    exit()

no_of_matches = len(matches)

# Allocate space for matched points
p1_image = np.zeros((no_of_matches, 2))
p2_image = np.zeros((no_of_matches, 2))

# Store coordinates of the matched points
for i in range(len(matches)):
    p1_image[i, :] = kp1[matches[i].queryIdx].pt
    p2_image[i, :] = kp2[matches[i].trainIdx].pt

# Find the homography matrix
homography, mask = cv2.findHomography(p1_image, p2_image, cv2.RANSAC)

# Print the homography matrix
print("Homography matrix:")
print(homography)

# Decompose the homography matrix
tx, ty, sx, sy, angle = decompose_homography(homography)

print(f"Translation: tx = {tx}, ty = {ty}")
print(f"Scaling: sx = {sx}, sy = {sy}")
print(f"Rotation angle: {angle} degrees")

# Compute the inverse homography matrix
inverse_homography = np.linalg.inv(homography)
# Warp the first image to align with the second image
transformed_img = cv2.warpPerspective(img1, inverse_homography, (width, height))

# Save the transformed image
cv2.imwrite('CalibOutput.jpg', transformed_img)

# Create a 2x2 subplot layout
fig, axs = plt.subplots(2, 2, figsize=(10, 10))

# Plot the first original image
axs[0, 0].imshow(cv2.cvtColor(cv2.flip(img1, 0), cv2.COLOR_BGR2RGB))
axs[0, 0].set_title('Calibration Pattern')
axs[0, 0].axis('off')

# Plot the second original image
axs[0, 1].imshow(cv2.cvtColor(img2, cv2.COLOR_BGR2RGB))
axs[0, 1].set_title('Recorded Image')
axs[0, 1].axis('off')

# Compute the difference image
diff_img = cv2.absdiff(img2, img1)
# Plot the difference image between img2 and img1
axs[1, 0].imshow(cv2.cvtColor(diff_img, cv2.COLOR_BGR2RGB))
axs[1, 0].set_title('Difference Image (img2 - img1)')
axs[1, 0].axis('off')


# Plot the transformed image
axs[1, 1].imshow(cv2.cvtColor(transformed_img, cv2.COLOR_BGR2RGB))
axs[1, 1].set_title('Transformed Image (mapping 1 onto 2)')
axs[1, 1].axis('off')

# Adjust layout
plt.tight_layout()

# Show plot
plt.show()

# Compute the inverse homography matrix
inverse_homography = np.linalg.inv(homography)

# Print the inverse homography matrix
print("Inverse Homography matrix:")
print(inverse_homography)

# # Warp img3 using the inverse homography matrix
# height3, width3, _ = img3.shape
# inverse_transformed_img3 = cv2.warpPerspective(img3, inverse_homography, (width3, height3))

# # Save the inverse transformed image
# cv2.imwrite('inverse_output.jpg', inverse_transformed_img3)

# # Plot img3 and the inverse transformed image
# fig, axs = plt.subplots(1, 2, figsize=(12, 6))

# # Plot img3
# axs[0].imshow(cv2.cvtColor(img3, cv2.COLOR_BGR2RGB))
# axs[0].set_title('Original Image 3')
# axs[0].axis('off')

# # Plot the inverse transformed image
# axs[1].imshow(cv2.cvtColor(inverse_transformed_img3, cv2.COLOR_BGR2RGB))
# axs[1].set_title('Inverse Transformed Image 3')
# axs[1].axis('off')

# # Adjust layout
# plt.tight_layout()

# # Show plot
# plt.show()