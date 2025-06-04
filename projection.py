
import cv2
import numpy as np
from pathlib import Path
import os
from typing import Optional
# use an env-var override so you can change it without editing code again
SSD_ROOT = Path(os.getenv("STIM_DATA_DIR",
            "/media/aharonilabjetson2/NVMe/stimviewer_data")).expanduser()
SSD_ROOT.mkdir(parents=True, exist_ok=True)      # auto-create on first run

from PyQt5.QtWidgets import  QLabel, QMainWindow
from PyQt5.QtGui import QPixmap, QImage

app = None
image_window = None  # Store the window globally

class ProjectDisplay(QMainWindow):
    def __init__(self, screen):
        super().__init__()

        self.screen = screen
        self.label = QLabel(self)
        self.setCentralWidget(self.label)
        self.move(screen.geometry().x(), screen.geometry().y())
        self.resize(screen.geometry().width(), screen.geometry().height())
        self.showFullScreen()

    def update_image(self, image):
        """Updates the displayed image."""
        height, width, channels = image.shape
        bytes_per_line = channels * width
        qimage = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(qimage))

    # def show_image_fullscreen_on_second_monitor(self, image, homography_matrix=None):
    #     """Displays an image on the second monitor using PyQt without threading issues."""

    #     if homography_matrix is None:
    #         homography_matrix = np.eye(3)

    #     # Apply Homography Transformation
    #     image_transformed = cv2.warpPerspective(image, homography_matrix, (image.shape[1], image.shape[0]))
    #     image_transformed = cv2.cvtColor(image_transformed, cv2.COLOR_BGR2RGB)  # Convert to RGB

    #     image_transformed = cv2.flip(image_transformed, 1)

    #     # ✅ Directly update the image (since we're in the GUI thread)
    #     self.update_image(image_transformed)



    def show_image_fullscreen_on_second_monitor(
            self,
            image: np.ndarray,
            homography_matrix: Optional[np.ndarray] = None, mirror: bool = True
    ):
        """
        Display `image` full-screen on the chosen monitor.

        Parameters
        ----------
        image : np.ndarray
            BGR image in *camera* coordinates if `homography_matrix`
            is provided, otherwise already in projector coordinates.
        homography_matrix : np.ndarray | None
            3×3 camera→projector homography.  If None, no warp is applied.
        mirror : bool, default True
            Flip horizontally before display (keeps legacy behaviour).
        """
        img_to_show = image

        # 1) optional warp
        if homography_matrix is not None:
            h, w = image.shape[:2]
            img_to_show = cv2.warpPerspective(
                image,
                homography_matrix,
                (w, h),
                flags=cv2.INTER_NEAREST,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0
            )

        # 2) BGR → RGB
        img_to_show = cv2.cvtColor(img_to_show, cv2.COLOR_BGR2RGB)

        # 3) optional mirror
        if mirror:
            img_to_show = cv2.flip(img_to_show, 1)

        # 4) send to the label
        self.update_image(img_to_show)
