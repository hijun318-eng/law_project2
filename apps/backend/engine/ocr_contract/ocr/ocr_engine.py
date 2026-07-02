"""
OCR 엔진 모듈

PaddleOCR를 래핑하여 이미지에서 한국어 텍스트를 추출한다.
- 지연 초기화(lazy init)로 모듈 임포트 시 모델 로딩을 막는다.
- 이미지 리사이즈로 OCR 품질과 처리 속도를 최적화한다.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PIL import Image

# PaddlePaddle >= 3.x PIR OneDNN 호환성 문제 우회
os.environ.setdefault("FLAGS_enable_pir_api", "0")

_MAX_OCR_WIDTH = 1500


def _resize_for_ocr(image_path: str) -> str:
    """
    이미지를 OCR에 적합한 크기로 리사이즈한다.

    - 원본 비율을 유지한다.
    - _MAX_OCR_WIDTH 이하이면 원본 경로를 그대로 반환한다.
    - RGBA/P 모드(투명도)는 PNG로, 나머지는 JPG로 저장한다.

    Returns:
        리사이즈된 임시 파일 경로 또는 원본 경로
    """
    img = Image.open(image_path)

    if img.width <= _MAX_OCR_WIDTH:
        return image_path

    ratio = _MAX_OCR_WIDTH / img.width
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.LANCZOS)

    suffix = ".png" if img.mode in ("RGBA", "P") else ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    save_kwargs: dict = {} if suffix == ".png" else {"quality": 95, "optimize": True}
    img.save(tmp.name, **save_kwargs)

    return tmp.name


def _get_paddle_ocr():
    """
    PaddleOCR 인스턴스를 지연 초기화(lazy init)로 반환한다.
    첫 호출 시에만 모델을 로딩하고 이후 호출에는 캐시된 인스턴스를 재사용한다.
    """
    if not hasattr(_get_paddle_ocr, "_instance"):
        from paddleocr import PaddleOCR
        _get_paddle_ocr._instance = PaddleOCR(lang="korean")
    return _get_paddle_ocr._instance


def run_ocr(image_path: str) -> str:
    """
    이미지에서 한국어 텍스트를 추출한다.

    Args:
        image_path: 근로계약서 이미지 파일 경로

    Returns:
        OCR로 인식된 전체 텍스트 (줄바꿈 구분)

    Raises:
        FileNotFoundError: 이미지 파일이 존재하지 않는 경우
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    print("🔍 OCR 텍스트 추출 중...")
    resized_path = _resize_for_ocr(image_path)

    engine = _get_paddle_ocr()
    result = engine.ocr(resized_path, cls=False)

    raw = result[0] if result else []
    texts = [line[1][0] for line in raw if line[1][1] > 0.5]

    return "\n".join(t.strip() for t in texts if t.strip())
