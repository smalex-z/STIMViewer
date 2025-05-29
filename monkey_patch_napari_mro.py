# # monkey_patch_napari_mro.py
# import napari._qt.containers._base_item_model as _bm
# from PyQt5.QtCore import QAbstractItemModel

# # Scan every class in the module and, if it inherits QAbstractItemModel
# # but doesn’t list it first, move it to the front of the MRO.
# for name in dir(_bm):
#     cls = getattr(_bm, name)
#     if isinstance(cls, type):
#         bases = list(getattr(cls, "__bases__", []))
#         if QAbstractItemModel in bases and bases[0] is not QAbstractItemModel:
#             i = bases.index(QAbstractItemModel)
#             bases.insert(0, bases.pop(i))
#             cls.__bases__ = tuple(bases)
