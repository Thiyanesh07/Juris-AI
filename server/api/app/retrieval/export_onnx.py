"""ONNX exporter for law-ai/InLegalBERT model."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import get_data_dir, get_settings

logger = logging.getLogger(__name__)


def get_onnx_model_path(data_dir: Path | None = None) -> Path:
    base_data = (data_dir or get_data_dir()).resolve()
    return base_data / "models" / "inlegalbert" / "model.onnx"


def export_inlegalbert_onnx(
    model_name: str = "law-ai/InLegalBERT",
    output_path: Path | None = None,
    opset_version: int = 14,
) -> Path:
    """Export HuggingFace InLegalBERT model to FP32 ONNX format."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    target_path = output_path or get_onnx_model_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading PyTorch model %s for ONNX export...", model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    dummy_text = ["This is a sample legal sentence for ONNX model export."]
    inputs = tokenizer(
        dummy_text,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    input_names = ["input_ids", "attention_mask"]
    dummy_inputs: tuple[Any, ...] = (inputs["input_ids"], inputs["attention_mask"])

    dynamic_axes: dict[str, dict[int, str]] = {
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "last_hidden_state": {0: "batch_size", 1: "sequence_length"},
    }

    if "token_type_ids" in inputs:
        input_names.append("token_type_ids")
        dummy_inputs = (inputs["input_ids"], inputs["attention_mask"], inputs["token_type_ids"])
        dynamic_axes["token_type_ids"] = {0: "batch_size", 1: "sequence_length"}

    class OnnxEncoderWrapper(torch.nn.Module):
        def __init__(self, base_model: Any) -> None:
            super().__init__()
            self.base_model = base_model

        def forward(
            self,
            input_ids: torch.Tensor,
            attention_mask: torch.Tensor,
            token_type_ids: torch.Tensor | None = None,
        ) -> torch.Tensor:
            kwargs: dict[str, torch.Tensor] = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
            if token_type_ids is not None:
                kwargs["token_type_ids"] = token_type_ids
            return self.base_model(**kwargs).last_hidden_state

    wrapper = OnnxEncoderWrapper(model)
    wrapper.eval()

    logger.info("Exporting ONNX graph to %s...", target_path)
    with torch.inference_mode():
        torch.onnx.export(
            wrapper,
            dummy_inputs,
            str(target_path),
            input_names=input_names,
            output_names=["last_hidden_state"],
            dynamic_axes=dynamic_axes,
            opset_version=opset_version,
            do_constant_folding=True,
            dynamo=False,
        )

    file_size_mb = target_path.stat().st_size / (1024 * 1024)
    logger.info("Successfully exported ONNX model to %s (%.2f MB)", target_path, file_size_mb)
    return target_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    path = export_inlegalbert_onnx(model_name=settings.embedding_model_name)
    print(f"Exported model to: {path} ({path.stat().st_size / (1024*1024):.2f} MB)")
