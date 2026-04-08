from __future__ import annotations

import os

from PIL import Image
from ultralytics import YOLO

from bots.base.abstract import AbstractDatabot
from config import config
from core.domain.DatabotRole import DatabotRole
from services.coco_builder import CocoBuilder
from utils.types import Score


class CocoBboxDetectorDatabot(AbstractDatabot):
    NAME = "coco-bbox-detector"
    DESCRIPTION = (
        "Runs YOLO object detection on herbarium sheet thumbnails, "
        "produces per-image bbox results (COCO xywh) stored in databot_results "
        "and optionally writes a merged COCO JSON file for the whole batch."
    )
    VERSION = 1
    ROLE = DatabotRole.SCANNER

    def __init__(self):
        super().__init__()
        bot_cfg = config.get_bot_config(self.NAME) or {}
        weights = bot_cfg.get("weights_path") or os.getenv(
            "YOLO_WEIGHTS_PATH", "/app/weights/model.pt"
        )
        self.conf_threshold = float(bot_cfg.get("conf_threshold") or os.getenv("YOLO_CONF", "0.25"))
        self.device = bot_cfg.get("device") or os.getenv("YOLO_DEVICE", "cpu")
        self.output_coco_path = bot_cfg.get("output_coco_path") or os.getenv("OUTPUT_COCO_PATH", "")

        self.model = YOLO(weights)
        self.category_names: dict[int, str] = dict(self.model.names)
        print(
            f"  YOLO model loaded: {weights}  "
            f"({len(self.category_names)} classes, conf≥{self.conf_threshold}, device={self.device})"
        )

    # ------------------------------------------------------------------
    # Per-image inference (called by AbstractDatabot.run for each record)
    # ------------------------------------------------------------------

    def compute(self, image_local_path: str) -> Score:
        img = Image.open(image_local_path)
        width, height = img.size

        results = self.model.predict(
            source=image_local_path,
            conf=self.conf_threshold,
            device=self.device,
            verbose=False,
        )
        detections = _extract_detections(results, self.category_names)

        return {
            "width": width,
            "height": height,
            "detections": detections,
        }

    # ------------------------------------------------------------------
    # Overridden run(): same per-record loop + COCO accumulation
    # ------------------------------------------------------------------

    def run(self):
        builder = CocoBuilder(self.category_names)
        records = self.DATABASE.fetch_records(self.DB_ID)

        for record in records:
            rec_id = record["id"]
            thumb_key = record["databot_thumb_filename"]
            local_path = None
            try:
                local_path = self.s3storage.download_file(thumb_key)
                result = self.compute(local_path)

                self.DATABASE.save_success_result(self.DB_ID, rec_id, result)

                builder.add_image(
                    image_id=rec_id,
                    file_name=thumb_key,
                    width=result["width"],
                    height=result["height"],
                )
                for det in result["detections"]:
                    builder.add_annotation(
                        image_id=rec_id,
                        bbox_xywh=det["bbox"],
                        area=det["area"],
                        category_id=det["category_id"],
                        score=det["confidence"],
                    )
            except Exception as e:
                self.DATABASE.save_error_result(self.DB_ID, rec_id, str(e))
                print(f"❌ {rec_id} -> {e}")
            finally:
                if local_path:
                    self.s3storage.cleanup_file(local_path)

        if self.output_coco_path:
            os.makedirs(os.path.dirname(self.output_coco_path) or ".", exist_ok=True)
            with open(self.output_coco_path, "w", encoding="utf-8") as f:
                f.write(builder.to_json())
            print(
                f"📄 COCO JSON written to {self.output_coco_path} "
                f"({builder.image_count} images, {builder.annotation_count} annotations)"
            )
        else:
            print(
                f"✅ Batch done: {builder.image_count} images, "
                f"{builder.annotation_count} annotations (no file output configured)"
            )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_detections(results, category_names: dict[int, str]) -> list[dict]:
    """Convert Ultralytics Results list to a flat list of COCO-style dicts."""
    detections: list[dict] = []
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            w = x2 - x1
            h = y2 - y1
            cat_id = int(box.cls[0].item())
            detections.append({
                "bbox": [round(x1, 2), round(y1, 2), round(w, 2), round(h, 2)],
                "area": round(w * h, 2),
                "category_id": cat_id,
                "category_name": category_names.get(cat_id, str(cat_id)),
                "confidence": round(float(box.conf[0].item()), 4),
            })
    return detections
