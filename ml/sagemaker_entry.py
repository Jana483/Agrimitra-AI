"""
Optional SageMaker inference entry for crop suitability.

The API uses the rules in app.py until SAGEMAKER_ENDPOINT_NAME is set.
This module is the script a SageMaker scikit-learn container would load.
"""

import json
import os


def model_fn(model_dir):
    path = os.path.join(model_dir, "crop_rules.json")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(__file__), "..", "data", "crop_rules.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def input_fn(body, content_type="application/json"):
    if content_type != "application/json":
        raise ValueError("AgriMitra SageMaker input must be JSON")
    return json.loads(body)


def predict_fn(payload, model):
    season = payload.get("season", "Kharif")
    soil = payload.get("soil", "Black Soil")
    water = payload.get("water_availability", "Medium")
    ranked = []
    for crop in model.get("crops", []):
        if season not in crop.get("seasons", []) and "All" not in crop.get("seasons", []):
            continue
        score = 60
        if soil in crop.get("suitable_soils", []):
            score += 20
        if water == crop.get("water_requirement"):
            score += 15
        elif water == "Low" and crop.get("water_requirement") == "High":
            score -= 30
        ranked.append({
            "name": crop.get("name"),
            "suitability_score": max(35, min(98, score)),
            "water_requirement": crop.get("water_requirement"),
        })
    ranked.sort(key=lambda row: row["suitability_score"], reverse=True)
    return {"model": "agrimitra-crop-rules", "top_recommendations": ranked[:5]}


def output_fn(prediction, accept="application/json"):
    return json.dumps(prediction), accept
