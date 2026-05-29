from fastapi import APIRouter, HTTPException
from src.ml.model import load_metadata, load_training_history, model_is_trained
from src.ml.explainer import get_feature_importance
from src.ml.inference import predict_for_all, get_inference_summary

router = APIRouter(tags=["ml"])


@router.get("/ml/status")
def ml_status() -> dict:
    trained = model_is_trained()
    meta = load_metadata() if trained else None
    return {"is_trained": trained, "metadata": meta}


@router.post("/ml/train")
def train_model() -> dict:
    try:
        from scripts.train_model import run as train_run
        result = train_run(augment=True, cv_folds=5, verbose=False)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/ml/predictions")
def ml_predictions() -> list[dict]:
    return predict_for_all()


@router.get("/ml/feature-importance")
def feature_importance() -> list[dict]:
    return get_feature_importance()


@router.get("/ml/summary")
def ml_summary() -> dict:
    return get_inference_summary()


@router.get("/ml/history")
def ml_history() -> list[dict]:
    return load_training_history()
