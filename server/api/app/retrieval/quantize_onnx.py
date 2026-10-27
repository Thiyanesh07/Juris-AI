"""Dynamic INT8 Quantizer for InLegalBERT ONNX Model."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import get_data_dir, get_settings
from app.retrieval.export_onnx import export_inlegalbert_onnx, get_onnx_model_path

logger = logging.getLogger(__name__)


def get_onnx_int8_model_path(data_dir: Path | None = None) -> Path:
    base_data = (data_dir or get_data_dir()).resolve()
    target = base_data / "models" / "inlegalbert" / "model_int8.onnx"
    if not target.is_file():
        default_target = Path("data/models/inlegalbert/model_int8.onnx").resolve()
        if default_target.is_file():
            return default_target
    return target


def quantize_inlegalbert_int8(
    input_fp32_path: Path | None = None,
    output_int8_path: Path | None = None,
) -> Path:
    """Quantize FP32 ONNX model to INT8 using ONNX Runtime dynamic quantization."""
    from onnxruntime.quantization import QuantType, quantize_dynamic

    fp32_path = input_fp32_path or get_onnx_model_path()
    int8_path = output_int8_path or get_onnx_int8_model_path()

    if not fp32_path.is_file():
        logger.info("FP32 ONNX model not found at %s. Exporting FP32 first...", fp32_path)
        export_inlegalbert_onnx(output_path=fp32_path)

    int8_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Quantizing FP32 model %s to INT8 model at %s...", fp32_path, int8_path)

    quantize_dynamic(
        model_input=str(fp32_path),
        model_output=str(int8_path),
        weight_type=QuantType.QUInt8,
        op_types_to_quantize=["MatMul", "Attention", "Gather"],
    )

    fp32_size_mb = fp32_path.stat().st_size / (1024 * 1024)
    int8_size_mb = int8_path.stat().st_size / (1024 * 1024)
    logger.info(
        "Successfully generated INT8 ONNX model: %.2f MB (FP32: %.2f MB, Reduction: %.1f%%)",
        int8_size_mb,
        fp32_size_mb,
        (1.0 - int8_size_mb / fp32_size_mb) * 100.0,
    )
    return int8_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = quantize_inlegalbert_int8()
    print(f"Exported INT8 model to: {path} ({path.stat().st_size / (1024*1024):.2f} MB)")
