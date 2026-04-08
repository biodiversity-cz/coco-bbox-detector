from __future__ import annotations

import json
from datetime import datetime, timezone


class CocoBuilder:
    """Accumulates COCO detection-format JSON across multiple images."""

    def __init__(self, category_names: dict[int, str]):
        self._images: list[dict] = []
        self._annotations: list[dict] = []
        self._annotation_id = 1
        self._categories = [
            {"id": cat_id, "name": name, "supercategory": ""}
            for cat_id, name in sorted(category_names.items())
        ]

    def add_image(self, image_id: int, file_name: str, width: int, height: int) -> None:
        self._images.append({
            "id": image_id,
            "file_name": file_name,
            "width": width,
            "height": height,
        })

    def add_annotation(
        self,
        image_id: int,
        bbox_xywh: list[float],
        area: float,
        category_id: int,
        score: float,
    ) -> None:
        self._annotations.append({
            "id": self._annotation_id,
            "image_id": image_id,
            "category_id": category_id,
            "bbox": [round(v, 2) for v in bbox_xywh],
            "area": round(area, 2),
            "score": round(score, 4),
            "iscrowd": 0,
            "segmentation": [],
        })
        self._annotation_id += 1

    def build(self) -> dict:
        return {
            "info": {
                "description": "COCO bbox detection output (coco-bbox-detector databot)",
                "date_created": datetime.now(timezone.utc).isoformat(),
            },
            "images": self._images,
            "annotations": self._annotations,
            "categories": self._categories,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.build(), ensure_ascii=False, indent=indent)

    @property
    def image_count(self) -> int:
        return len(self._images)

    @property
    def annotation_count(self) -> int:
        return len(self._annotations)
