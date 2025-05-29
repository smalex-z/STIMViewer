# roi_editor.py


# 
# os.environ["NAPARI_OGL"] = "False" 
import os

os.environ["QT_LOGGING_RULES"]      = "qt.qpa.*=false"
os.environ['NAPARI_OGL'] = 'false'


import numpy as np, cupy as cp, napari
from magicgui import magicgui
from roi_thresh import threshold_patch
from otsu_thresh import load_movie, compute_mean_projection   # your file



def refine_rois(mean, labels):
    print("test")
    # Stream 5400 frames average them and return a 2-D float array as the background
    #mean  = compute_mean_projection(load_movie("cropped.avi"), calib_frames=5400)

    # --- 1) initial masks ----------------------------------------
    stack = labels
    # stack = np.load("rois.npz")["masks"]   # load the initial masks where rois.npz is the initial thresholding mask from main.py with N boolean masks
    # labels0 = np.zeros(mean.shape, np.int16) # empty integer image same dims as mean as the label map
    labels0 = np.zeros(mean.shape, np.int16)
    for i, m in enumerate(stack, 1): # start enumerating masks skipping label 0 
        if m.shape != mean.shape: # check the size
            raise ValueError("mask shape mismatch")
        labels0[m.astype(bool) & (labels0 == 0)] = i   # write label i into pixels where mask is True and no occupied hence (labels0==0)

    # Check if labels are assigned
    print("unique IDs now:", np.unique(labels0)[:20])
    viewer = napari.current_viewer() # or napari.Viewer()  # get the current viewer or create a new one
    print("passed napari current")
# Open window
    viewer.mouse_double_click_callbacks.clear() # Clear double click zoom in feature
    # viewer.add_image(mean, name="mean", colormap="gray", blending="additive")
    vmin, vmax = np.percentile(mean, (1, 99.5))   # Stretch the contrast of the mean image for clearer mean image
    viewer.add_image(mean.astype("float32"), # add the mean image as a grayscale
                    name="mean",
                    colormap="gray",
                    contrast_limits=(vmin, vmax),
                    blending="additive") # adds label map as a semi transparent overlay
    print("passed viewer add image")
    lbl = viewer.add_labels( # use a copy of the labels for future use
        labels0.copy(),
        name="ROIs",
        opacity=0.6,         # 60% visible
        blending="translucent",
    )
    print("passed viewer add labels")

    qt_canvas = viewer.window.qt_viewer.canvas
    print("passed viewer add labels")
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(
        0,
        lambda: (
            qt_canvas.update(),            # VisPy repaint
            qt_canvas.native.update(),     # Qt widget repaint
        )
    )
    print("passed viewer add labels")

    #lbl.color_mode = "random"
    lbl.contour = 1 # Give each roi a random color contour
    PAD      = 5        # pixels around ROI when cropping
    @lbl.mouse_double_click_callbacks.append ## appends mouse double clicks to the refine one function
    def refine_one(layer, event):
        event.handled = True # clear any previous double clicks
        r, c = map(int, event.position) # pick the pixel and roi id
        rid  = layer.data[r, c]
        if rid == 0:
            return
        # get the current mask for that roi and its bounding box
        mask = layer.data == rid
        ys, xs = np.where(mask)
        if ys.size == 0:        # no pixels (shouldn’t happen, but safe)
            return
        # extract the mean image patch with padding so the ROI mask isnt cut off from the box
        # PAD is the pixel margin on all sides, too small threshold might cut off edges of the cell
        # too big might have neighboring cells invade the patch
        # what if there is a way we can just extract the roi mask shape
        # put that into an empty black box and then run thresholding on that and then replace the old shape
        # instead of cutting out a box from the original mask which might have neighboring ROIs
        y0, y1 = ys.min() - PAD, ys.max() + PAD + 1
        x0, x1 = xs.min() - PAD, xs.max() + PAD + 1
        patch  = mean[y0:y1, x0:x1]
        if patch.size == 0:
            return
        # call threshold path to get a better mask, we can also change this for what type of ROI we clicked on
        # so we can call a custom threshold for all types of ROIs
        new_masks, _ = threshold_patch(patch)
        if not new_masks:
            viewer.status = "No new mask found"
            return  
        # which ever mask has a better i o u we update the old mask
        # iou is the overlap between two masks, shared pixels/pixels in either mask
        # so if the new mask shares more pixels with the old one its a better fit because it fit tighter over the original ROI
        # but may want to change this for different ROI fits, some original masks might be missing part of the ROI
        best, best_iou = None, 0
        for m in new_masks:
            iou = (m & mask[y0:y1,x0:x1]).sum() / (m | mask[y0:y1,x0:x1]).sum()
            if iou > best_iou:
                best, best_iou = m, iou 

        layer.data[mask] = 0 # live label image napari is displaying
        # mask is a boolean array same shape as layer.data that is True for every pixel of the old ROI
        # setting them to 0 erases the previous ROI from the map
        layer.data[y0:y1, x0:x1][best] = rid # then we select the cropped region around the ROI the same coordinates to build the patch
        # then those are set to the original ROI ID rid

        # quick flash
        old_opacity = layer.opacity # store the current opacity
        layer.opacity = min(1.0, old_opacity + 0.4) # make the label brighter 
        from PyQt5.QtCore import QTimer # import short timer
        QTimer.singleShot(400, lambda: setattr(layer, "opacity", old_opacity))
        # call back 400 ms later that sets the layer opacity to the original value
        # single shot ensures we dont have a persistent timer object
        viewer.status = f"ROI {rid} refined (IoU {best_iou:.2f})"
            # update the status bar of napari

    # ---------------- selection widgets --------------------------
    from PyQt5.QtWidgets import QLabel
    from PyQt5.QtCore    import Qt

    selected: set[int] = set()   # hold all ROI IDs the user marked 

    # create label that shows what ROIs where selected
    sel_label = QLabel('Selected ROIs: none')
    sel_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    sel_label.setWordWrap(True)           # allow multi-line text

    # show the current selected ROIs
    def refresh_sel_label() -> None:
        """Update the label to show current keep-list."""
        text = ', '.join(map(str, sorted(selected))) or 'none'
        sel_label.setText(f'Selected ROIs: {text}')

    # @pyqtSlot(object, object)
    # def _launch_napari_viewer(self, mean, masks):
    #     # This will find the existing embedded Viewer:
    #     from napari import current_viewer
    #     viewer = current_viewer()
    #     if viewer is None:
    #         # fallback: create one (but you should already have one)
    #         from napari import Viewer
    #         viewer = Viewer()

    #     # Now **add** your layers onto it
    #     label_map = refine_rois(mean, masks) 

    # uses magic gui to build a QT button to toggle the ROI based on the function its over
    @magicgui(call_button='Toggle select ROI')
    def toggle(id: int = 1):
        """Add or remove an ROI ID from the keep-list."""
        selected.symmetric_difference_update([id])
        refresh_sel_label()

    # if nothing selected shows status
    @magicgui(call_button='Keep only selected')
    def keep():
        """Hide every ROI *not* in the keep-list."""
        if not selected:
            viewer.status = "Nothing selected."
            return
        lbl.data[~np.isin(lbl.data, list(selected))] = 0 # build a boolean mask of pixels whose labels are in selected and uses ~ to invert them
        # those are set to 0 all unselected ROis disappear
        viewer.status = f"Kept {len(selected)} ROIs"

    # restores the original label map and empties selected map
    @magicgui(call_button='Reset masks')
    def reset():
        """Restore original masks and clear the keep-list."""
        lbl.data = labels0.copy()
        selected.clear()
        refresh_sel_label()
        viewer.status = "Mask reset"

    # saves the current label image to rois_current.npz
    @magicgui(call_button='Export → trace_view')
    def export():
        """Write the current label map for the next stage."""
        np.savez_compressed("rois_current.npz", labels=lbl.data)
        viewer.status = "Exported rois_current.npz"


    # ---- dock widgets -------------------------------------------
    for w in (toggle, keep, reset, export):
        viewer.window.add_dock_widget(w, area='right')

    viewer.window.add_dock_widget(sel_label, area='right')
    refresh_sel_label()        # initialize text once
    return labels0

    # qt_viewer = viewer.window.qt_viewer 
    # canvas    = qt_viewer.canvas   
    # canvas.update()     

    # try:
    #     canvas.native.update()                             # the actual Qt widget’s update   
    # except AttributeError:
    #     pass  

    # # 4) Let Qt process that draw before returning  
    # from PyQt5.QtWidgets import QApplication
    # QApplication.processEvents()  


# import sys
# import numpy as np
# import cv2
# from PyQt5.QtWidgets import (
#     QApplication, QWidget, QVBoxLayout, QHBoxLayout,
#     QPushButton, QLabel, QMessageBox
# )
# from PyQt5.QtCore import Qt, pyqtSignal
# import pyqtgraph as pg
# from roi_thresh import threshold_patch
# from otsu_thresh import load_movie, compute_mean_projection

# class ROIEditor(QWidget):
#     """
#     PyQt5 + PyQtGraph ROI editor.
#     Click on ROI pixels to select (single-click) or refine (double-click).
#     Emits `closed` when the window is closed.
#     """
#     closed = pyqtSignal()

#     def __init__(self, mean: np.ndarray, masks: np.ndarray, parent=None):
#         super().__init__(parent)
#         self.mean = mean
#         self.orig_masks = masks.copy()
#         self.labels = self._make_label_map(mean.shape, masks)
#         self.selected = set()
#         self.num_rois = masks.shape[0]
#         self.init_ui()

#     def _make_label_map(self, shape, masks):
#         lbl = np.zeros(shape, dtype=np.int32)
#         for i, m in enumerate(masks, 1):
#             lbl[m.astype(bool)] = i
#         return lbl

#     def init_ui(self):
#         self.setWindowTitle('ROI Editor')
#         layout = QVBoxLayout(self)

#         # Image and ROI overlay
#         self.view = pg.GraphicsLayoutWidget()
#         layout.addWidget(self.view)
#         self.vb = self.view.addViewBox()
#         self.vb.setAspectLocked(True)
#         self.vb.setMouseEnabled(x=False, y=False) 

#         self.img_item = pg.ImageItem(self.mean.astype(np.float32))
#         self.vb.addItem(self.img_item)

#         self.label_item = pg.ImageItem(self.labels.astype(np.int32), opacity=0.6)
#         self.label_item.setAcceptedMouseButtons(Qt.LeftButton)
#         self.label_item.setZValue(10)   
#         lut = np.zeros((self.num_rois+1,4), dtype=np.uint8)
#         lut[0] = [0,0,0,0]
#         rng = np.random.RandomState(0)
#         for i in range(1, self.num_rois+1):
#             lut[i] = [*rng.randint(0,256,3),150]
#         self.label_item.setLookupTable(lut)
#         self.vb.addItem(self.label_item)

#         self.label_item.mouseClickEvent = self._handle_click
#         # Capture clicks on the viewbox scene
#         #self.vb.scene().sigMouseClicked.connect(self.on_click)

#         # Info and selection labels
#         self.info_label = QLabel('Click on ROI: single-click select, double-click refine')
#         layout.addWidget(self.info_label)
#         self.sel_label = QLabel('Selected ROIs: none')
#         layout.addWidget(self.sel_label)

#         # Control buttons
#         btn_layout = QHBoxLayout()
#         self.reset_btn = QPushButton('Reset')
#         self.keep_btn = QPushButton('Keep Selected')
#         self.show_btn = QPushButton('Show Selected')
#         self.export_btn = QPushButton('Export & Close')
#         for b in (self.reset_btn, self.keep_btn, self.show_btn, self.export_btn):
#             btn_layout.addWidget(b)
#         layout.addLayout(btn_layout)

#         # Connect buttons
#         self.reset_btn.clicked.connect(self.on_reset)
#         self.keep_btn.clicked.connect(self.on_keep)
#         self.show_btn.clicked.connect(self.on_show)
#         self.export_btn.clicked.connect(self.close)

#     # def on_click(self, event):
#     #     # Only left-clicks
#     #     if event.button() != Qt.LeftButton:
#     #         return
#     #     pos = event.scenePos()
#     #     if not self.vb.sceneBoundingRect().contains(pos):
#     #         return
#     #     pixel = self.vb.mapSceneToView(pos)
#     #     x, y = int(pixel.x()), int(pixel.y())
#     #     if x < 0 or y < 0 or x >= self.labels.shape[1] or y >= self.labels.shape[0]:
#     #         return
#     #     rid = int(self.labels[y, x])
#     #     if rid <= 0:
#     #         return
#     #     if event.double():
#     #         self.refine_roi(rid)
#     #     else:
#     #         self.toggle_selection(rid)

#     def toggle_selection(self, rid: int):
#         if rid in self.selected:
#             self.selected.remove(rid)
#         else:
#             self.selected.add(rid)
#         sel = ', '.join(map(str, sorted(self.selected))) or 'none'
#         self.sel_label.setText(f'Selected ROIs: {sel}')

#     def refine_roi(self, rid: int):
#         mask = (self.labels == rid)
#         ys, xs = np.where(mask)
#         y0, y1 = ys.min(), ys.max()
#         x0, x1 = xs.min(), xs.max()
#         patch = self.mean[y0:y1+1, x0:x1+1]
#         new_masks, _ = threshold_patch(patch)
#         if not new_masks:
#             self.info_label.setText(f'ROI {rid}: no new mask')
#             return
#         best_iou, best = 0, None
#         old = mask[y0:y1+1, x0:x1+1]
#         for m in new_masks:
#             inter = (m & old).sum()
#             union = (m | old).sum()
#             iou = inter / union if union else 0
#             if iou > best_iou:
#                 best_iou, best = iou, m
#         if best is None:
#             self.info_label.setText(f'ROI {rid}: refine failed')
#             return
#         self.labels[mask] = 0
#         sub = np.zeros_like(old, bool)
#         sub[best] = True
#         self.labels[y0:y1+1, x0:x1+1][sub] = rid
#         self.label_item.setImage(self.labels.astype(np.int32))
#         self.info_label.setText(f'ROI {rid} refined (IoU={best_iou:.2f})')

#     def on_reset(self):
#         self.labels = self._make_label_map(self.mean.shape, self.orig_masks)
#         self.label_item.setImage(self.labels.astype(np.int32))
#         self.selected.clear()
#         self.sel_label.setText('Selected ROIs: none')
#         self.info_label.setText('Masks reset')

#     def on_keep(self):
#         if not self.selected:
#             self.info_label.setText('No ROIs selected')
#             return
#         mask = np.isin(self.labels, list(self.selected))
#         self.labels = np.where(mask, self.labels, 0)
#         self.label_item.setImage(self.labels.astype(np.int32))
#         self.info_label.setText(f'Kept {len(self.selected)} ROIs')

#     def on_show(self):
#         sel = ', '.join(map(str, sorted(self.selected))) or 'none'
#         QMessageBox.information(self, 'Selected ROIs', f'Selected ROIs: {sel}')

#     def closeEvent(self, event):
#         np.savez_compressed('rois_current.npz', masks=self.labels)
#         self.closed.emit()
#         event.accept()

#     def _handle_click(self, ev):
#         if ev.button() != Qt.LeftButton:
#             return
#         x, y = int(ev.pos().x()), int(ev.pos().y())   # image-local coords
#         if not (0 <= x < self.labels.shape[1] and 0 <= y < self.labels.shape[0]):
#             return

#         rid = int(self.labels[y, x])
#         if rid <= 0:            # background
#             return

#         if ev.double():         # ← pyqtgraph gives you this helper
#             self.refine_roi(rid)
#         else:
#             self.toggle_selection(rid)
#         ev.accept()      

# if __name__ == '__main__':
#     movie = load_movie('cropped.avi')
#     mean = compute_mean_projection(movie)
#     data = np.load('rois.npz')
#     masks = data['masks']
#     app = QApplication(sys.argv)
#     editor = ROIEditor(mean, masks)
#     editor.closed.connect(lambda: print('Saved rois_current.npz'))
#     editor.show()
#     sys.exit(app.exec_())

# """
# roi_editor_qt.py
# Standalone ROI editor replicating the functionality of the
# napari-based roi_editor.py but using pure PyQt5 + pyqtgraph.

# *Compatible with Python >= 3.6*  – we now import **Tuple** from the
# ``typing`` module instead of relying on the built‑in generics that were
# added only in Python 3.9.  This fixes the ``TypeError: 'type' object is
# not subscriptable`` you saw on Jetson/Python 3.8.

# Usage::

#     python roi_editor_qt.py  # assumes cropped.avi and rois.npz present
# """

# import sys
# from pathlib import Path
# from typing import Tuple  # ← NEW: keep 3.6/3.7/3.8 happy

# import numpy as np
# import cv2
# from PyQt5.QtWidgets import (
#     QApplication, QWidget, QVBoxLayout, QHBoxLayout,
#     QPushButton, QLabel, QMessageBox
# )
# from PyQt5.QtCore import Qt, pyqtSignal, QTimer
# import pyqtgraph as pg

# from roi_thresh import threshold_patch
# from otsu_thresh import load_movie, compute_mean_projection


# PAD = 5  # pixels of margin when refining a ROI


# class ROIEditor(QWidget):
#     """Interactive ROI editor.

#     * **single‑click** on a ROI → toggle selection
#     * **double‑click** on a ROI → re‑threshold that ROI (refine)
#     """

#     closed = pyqtSignal()

#     def __init__(self, mean: np.ndarray, masks: np.ndarray, parent=None):
#         super().__init__(parent)
#         self.mean = mean
#         self.orig_masks = masks.copy()
#         self.labels = self._make_label_map(mean.shape, masks)
#         self.selected: set[int] = set()
#         self.num_rois = masks.shape[0]
#         self._rng = np.random.RandomState(0)
#         self._build_ui()

#     # ------------------------------------------------------------------
#     # Data helpers
#     # ------------------------------------------------------------------
#     @staticmethod
#     def _make_label_map(shape: Tuple[int, int],  # ← changed
#                         masks: np.ndarray) -> np.ndarray:
#         """Compose a single 2‑D label image from a stack of boolean masks.

#         Pixels that belong to more than one mask are assigned to the *first*
#         mask that touches them (matching the napari behaviour).
#         """
#         lbl = np.zeros(shape, np.int16)
#         for i, m in enumerate(masks, 1):
#             lbl[m.astype(bool) & (lbl == 0)] = i
#         return lbl

#     # ------------------------------------------------------------------
#     # GUI
#     # ------------------------------------------------------------------
#     def _build_ui(self) -> None:
#         self.setWindowTitle("ROI Editor")
#         layout = QVBoxLayout(self)

#         # Contrast‑stretch the background for visibility
#         vmin, vmax = np.percentile(self.mean, (1, 99.5))
#         norm_mean = np.clip((self.mean - vmin) / (vmax - vmin), 0, 1)

#         self.canvas = pg.GraphicsLayoutWidget()
#         layout.addWidget(self.canvas)
#         self.vb = self.canvas.addViewBox(lockAspect=True)
#         self.vb.setMouseEnabled(x=False, y=False)

#         # background
#         self.img_item = pg.ImageItem(norm_mean.astype(np.float32))
#         self.vb.addItem(self.img_item)

#         # label overlay
#         self.label_item = pg.ImageItem(self.labels, opacity=0.6)
#         self.label_item.setLookupTable(self._make_lut())
#         self.label_item.setZValue(10)
#         self.label_item.setAcceptedMouseButtons(Qt.LeftButton)
#         self.label_item.mouseClickEvent = self._on_click
#         self.vb.addItem(self.label_item)

#         # info labels
#         self.info_label = QLabel(
#             "Click ROI: single‑click to toggle selection, double‑click to refine")
#         layout.addWidget(self.info_label)
#         self.sel_label = QLabel("Selected ROIs: none")
#         layout.addWidget(self.sel_label)

#         # buttons
#         btns = QHBoxLayout()
#         self.reset_btn = QPushButton("Reset")
#         self.keep_btn = QPushButton("Keep selected")
#         self.show_btn = QPushButton("Show selected")
#         self.export_btn = QPushButton("Export & close")
#         for b in (self.reset_btn, self.keep_btn,
#                   self.show_btn, self.export_btn):
#             btns.addWidget(b)
#         layout.addLayout(btns)

#         # connections
#         self.reset_btn.clicked.connect(self._on_reset)
#         self.keep_btn.clicked.connect(self._on_keep)
#         self.show_btn.clicked.connect(self._on_show)
#         self.export_btn.clicked.connect(self.close)

#         self.resize(900, 800)

#     def _make_lut(self) -> np.ndarray:
#         lut = np.zeros((self.num_rois + 1, 4), np.uint8)
#         lut[0] = (0, 0, 0, 0)
#         colors = self._rng.randint(0, 256, size=(self.num_rois, 3))
#         lut[1:, :3] = colors
#         lut[1:, 3] = 150
#         return lut

#     # ------------------------------------------------------------------
#     # ------------------------------------------------------------------
#     # Mouse interaction
#     # ------------------------------------------------------------------
#         # Fallback: also catch clicks that land on the *viewbox* (older
#         # pyqtgraph builds do not always deliver ImageItem.mouseClickEvent)
#         self.vb.scene().sigMouseClicked.connect(self._on_scene_click)

#     # ——— main handler when we *do* get the event from ImageItem ———
#     def _on_click(self, ev):
#         self._process_click(ev.pos(), ev.button(), ev.double())
#         ev.accept()

#     # ——— alternate handler when the click arrives via the ViewBox scene ———
#     def _on_scene_click(self, ev):
#         if ev.button() != Qt.LeftButton:
#             return
#         if not self.vb.sceneBoundingRect().contains(ev.scenePos()):
#             return
#         pt = self.vb.mapSceneToView(ev.scenePos())  # returns QPointF in data‐coords
#         self._process_click(pt, ev.button(), ev.double())

#     # ——— common logic ———
#     def _process_click(self, qpointf, button, is_double):
#         col, row = int(qpointf.x()), int(qpointf.y())
#         if not (0 <= row < self.labels.shape[0] and 0 <= col < self.labels.shape[1]):
#             return
#         rid = int(self.labels[row, col])
#         if rid == 0:
#             return
#         if is_double:
#             self._refine_roi(rid)
#         else:
#             self._toggle_selection(rid)

#     def _on_click(self, ev):
#         if ev.button() != Qt.LeftButton:
#             return
#         # Item‑local coordinates are image pixels
#         col, row = map(int, (ev.pos().x(), ev.pos().y()))
#         if not (0 <= row < self.labels.shape[0] and 0 <= col < self.labels.shape[1]):
#             return

#         rid = int(self.labels[row, col])
#         if rid == 0:
#             return

#         if ev.double():
#             self._refine_roi(rid)
#         else:
#             self._toggle_selection(rid)
#         ev.accept()

#     # ------------------------------------------------------------------
#     # ROI operations
#     # ------------------------------------------------------------------
#     def _toggle_selection(self, rid: int) -> None:
#         if rid in self.selected:
#             self.selected.remove(rid)
#         else:
#             self.selected.add(rid)
#         txt = ", ".join(map(str, sorted(self.selected))) or "none"
#         self.sel_label.setText(f"Selected ROIs: {txt}")

#     def _refine_roi(self, rid: int) -> None:
#         mask = self.labels == rid
#         ys, xs = np.where(mask)
#         if ys.size == 0:
#             return

#         y0, y1 = ys.min() - PAD, ys.max() + PAD + 1
#         x0, x1 = xs.min() - PAD, xs.max() + PAD + 1
#         # clip to bounds
#         y0, x0 = max(0, y0), max(0, x0)
#         y1, x1 = min(self.mean.shape[0], y1), min(self.mean.shape[1], x1)

#         patch = self.mean[y0:y1, x0:x1]
#         if patch.size == 0:
#             return

#         new_masks, _ = threshold_patch(patch)
#         if not new_masks:
#             self.info_label.setText(f"ROI {rid}: no new mask found")
#             return

#         old_local = mask[y0:y1, x0:x1]
#         best_iou, best = 0.0, None
#         for m in new_masks:
#             inter = (m & old_local).sum()
#             union = (m | old_local).sum()
#             iou = inter / union if union else 0
#             if iou > best_iou:
#                 best_iou, best = iou, m

#         if best is None:
#             self.info_label.setText(f"ROI {rid}: refinement failed")
#             return

#         self.labels[mask] = 0
#         self.labels[y0:y1, x0:x1][best] = rid
#         self.label_item.setImage(self.labels, autoLevels=False)

#         # flash
#         self._flash_label_item()
#         self.info_label.setText(f"ROI {rid} refined (IoU={best_iou:.2f})")

#     def _flash_label_item(self):
#         start_opacity = self.label_item.opacity()
#         self.label_item.setOpacity(min(1.0, start_opacity + 0.4))
#         QTimer.singleShot(400, lambda: self.label_item.setOpacity(start_opacity))

#     # ------------------------------------------------------------------
#     # Button slots
#     # ------------------------------------------------------------------
#     def _on_reset(self):
#         self.labels = self._make_label_map(self.mean.shape, self.orig_masks)
#         self.label_item.setImage(self.labels, autoLevels=False)
#         self.selected.clear()
#         self.sel_label.setText("Selected ROIs: none")
#         self.info_label.setText("Masks reset")

#     def _on_keep(self):
#         if not self.selected:
#             self.info_label.setText("No ROIs selected")
#             return
#         keep_mask = np.isin(self.labels, list(self.selected))
#         self.labels = np.where(keep_mask, self.labels, 0)
#         self.label_item.setImage(self.labels, autoLevels=False)
#         self.info_label.setText(f"Kept {len(self.selected)} ROIs")

#     def _on_show(self):
#         sel = ", ".join(map(str, sorted(self.selected))) or "none"
#         QMessageBox.information(self, "Selected ROIs", f"Selected ROIs: {sel}")

#     # ------------------------------------------------------------------
#     # Close / export
#     # ------------------------------------------------------------------
#     def closeEvent(self, ev):
#         np.savez_compressed("rois_current.npz", labels=self.labels)
#         self.closed.emit()
#         ev.accept()


# # ----------------------------------------------------------------------
# # Main entry‑point
# # ----------------------------------------------------------------------

# def main() -> None:
#     if not Path("cropped.avi").exists():
#         raise FileNotFoundError("cropped.avi not found")

#     mean = compute_mean_projection(
#         load_movie("cropped.avi"), calib_frames=5400)
#     masks = np.load("rois.npz")["masks"]

#     app = QApplication(sys.argv)
#     editor = ROIEditor(mean, masks)
#     editor.closed.connect(lambda: print("Exported → rois_current.npz"))
#     editor.show()
#     sys.exit(app.exec_())


# if __name__ == "__main__":
#     main()
