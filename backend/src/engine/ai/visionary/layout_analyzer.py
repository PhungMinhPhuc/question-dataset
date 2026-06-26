import os
# Must be set BEFORE torch/OpenMP loads (doclayout_yolo imports torch). Multiple
# OpenMP runtimes (torch + opencv + others) otherwise cause a hard segfault on
# Windows when YOLO runs. Mirrors the workaround already used in utils/parse_visuals.py.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from doclayout_yolo import YOLOv10
import pymupdf
from PIL import Image
from pathlib import Path
from PIL import ImageDraw

try:
    import torch
    torch.set_num_threads(1)
    import cv2
    cv2.setNumThreads(0)
except Exception:
    pass

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "doclayout_yolo_docstructbench_imgsz1024.pt"

# Default to CPU: GPU inference inside a web server commonly hits flaky cuDNN
# errors (CUDNN_STATUS_INTERNAL_ERROR) or VRAM contention. Layout detection on a
# handful of document pages is fast enough on CPU. Override with DOCLAYOUT_DEVICE.
_DEVICE = os.getenv("DOCLAYOUT_DEVICE", "cpu")

class DocLayoutEngine:
    # Initalization
    def __init__(self, device: str = _DEVICE):
        # Load DocLayout-YOLO model (requires local .pt weights)
        self.device = device
        self.model = YOLOv10(MODEL_PATH)

    # Analyze and crop IMG
    def analyze_and_crop_img(self, IMG_PATH, output_dir, page_idx, figure_coords):

        # Tạo thư mục 'extracted_figures' nằm cùng cấp với file IMG_PATH
        save_dir = Path(output_dir) / "extracted_figures"
        save_dir.mkdir(parents=True, exist_ok=True) # Tự động tạo thư mục nếu chưa có

        # Run DocLayout_YOLO
        results = self.model.predict(IMG_PATH, conf=0.25, device=self.device) # confidence threshold

        img = Image.open(IMG_PATH)
        img_width, img_height = img.size

        # Loop through each detected bounding box from YOLO
        for i, box in enumerate(results[0].boxes):
            # Get  the class index of the detected object
            cls = int(box.cls[0])
            # Convert the class index to the actual label name
            label = results[0].names[cls]

            # print("Detected:", label)   # DEBUG

            # Nếu là Figure 
            if label.lower() in {'figure', 'picture', 'image', 'fig'}:
                coords = box.xyxy[0].tolist() # [x1, y1, x2, y2]
                # Tính toán vị trí tương đối (ví dụ: ảnh nằm ở 1/3 trên của trang)
                relative_y = coords[1] / img_height
                relative_x = round((coords[2] - coords[0])/img_width, 2)
                # print(f"Page {page_idx} - Figure {i} horizontal_scale: {relative_x}") # DEBUG
                crop_img = img.crop((coords[0], coords[1], coords[2], coords[3]))
                crop_path = save_dir / f"fig_p{page_idx}_{i}_scale{relative_x}.png"
                crop_img.save(str(crop_path))
                figure_coords.append({
                    "path": crop_path,
                    "page": page_idx,
                    "bbox": coords,
                    "horizontal_scale": relative_x, # X-axis occupancy ratio to autonomously synthesize `\includegraphics`
                    "vertical_position": relative_y # Chỉ số để neo vào câu hỏi
                })
        return figure_coords
    

    def process_layout_engine(self, FILE_PATH, output_dir, progress_cb=None):
        is_pdf = FILE_PATH.lower().endswith(".pdf")
        figure_coords = []
        page_images = []

        if is_pdf:
            doc = pymupdf.open(FILE_PATH)
            total = doc.page_count
            for page_idx, page in enumerate(doc):
                # Render page to image
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2)) # (x scale, y scale)
                img_dir = Path(output_dir) / "pages"
                img_dir.mkdir(parents=True, exist_ok=True)
                img_path = img_dir / f"page_{page_idx}.png"
                pix.save(str(img_path))
                page_images.append(img_path)
                self.analyze_and_crop_img(img_path, output_dir, page_idx, figure_coords)
                if progress_cb:
                    try:
                        progress_cb(page_idx + 1, total)
                    except Exception:
                        pass
        else:
            img_dir = Path(output_dir) / "pages"
            img_dir.mkdir(parents=True, exist_ok=True)
            img = Image.open(FILE_PATH)
            img_path = img_dir / "page_0.png"
            img.save(img_path)
            page_images.append(img_path)
            self.analyze_and_crop_img(img_path, output_dir, 0, figure_coords)
        return page_images, figure_coords



    #     # Analyze and crop PDF
    # def analyze_and_crop_pdf(self, FILE_PATH, output_dir):
    #     doc = pymupdf.open(FILE_PATH)
    #     figure_coords = []

    #     for page_idx, page in enumerate(doc):
    #         # Render page to image
    #         pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2)) # (x scale, y scale)
    #         img_path = f"page_{page_idx}.png"
    #         pix.save(img_path)

    #         # Run DocLayout_YOLO
    #         results = self.model.predict(img_path, conf=0.25) # confidence threshold

    #         img = Image.open(img_path)
    #         img_width, img_height = img.size
    #         # Loop through each detected bounding box from YOLO
    #         for i, box in enumerate(results[0].boxes):
    #             # Get  the class index of the detected object
    #             cls = int(box.cls[0])
    #             # Convert the class index to the actual label name
    #             label = results[0].names[cls]

    #             # Nếu là Figure 
    #             if label.lower() == 'figure':
    #                 coords = box.xyxy[0].tolist() # [x1, y1, x2, y2]
    #                 # Tính toán vị trí tương đối (ví dụ: ảnh nằm ở 1/3 trên của trang)
    #                 relative_y = coords[1] / img_height
    #                 crop_img = img.crop((coords[0], coords[1], coords[2], coords[3]))
    #                 crop_path = f"{output_dir}/fig_{page_idx}_{i}.png"
    #                 crop_img.save(crop_path)
    #                 figure_coords.append({
    #                     "path": crop_path,
    #                     "page": page_idx,
    #                     "bbox": coords,
    #                     "vertical_position": relative_y # Chỉ số để neo vào câu hỏi
    #                 })
    #     return figure_coords