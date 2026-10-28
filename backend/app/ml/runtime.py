"""Load the frozen joblib bundle once per process.

The pipeline is never fitted, retuned or saved again. If the file, the package
versions or the expected contract do not match, prediction stays unavailable
and the rest of the website still runs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sys
import threading
from dataclasses import dataclass, field

import numpy as np

from app.core.config import Settings, get_settings, project_root
from app.ml.features import EXPECTED_FEATURE_COLUMNS, EXPECTED_HISTORY_COLUMNS

logger = logging.getLogger("chargeconnect.model")
_predict_slots = threading.BoundedSemaphore(2)

LIMITATIONS = (
    "This is a historical research result for a Palo Alto session in 2020. "
    "It is not live charger availability, a predicted departure time, or a guaranteed wait. "
    "The website's own session records are not model inputs."
)

REFERENCE_METRICS = {
    "precision": 0.1443,
    "recall": 0.7043,
    "f1": 0.2396,
    "roc_auc": 0.5906,
    "average_precision": 0.1741,
}
REFERENCE_MATRIX = [[7175, 10423], [738, 1758]]
REFERENCE_PARAMS = {"n_estimators": 200, "max_depth": None, "min_samples_leaf": 20, "random_state": 42}


@dataclass
class ModelRuntime:
    ready: bool = False
    reason: str | None = "The historical model has not been loaded."
    bundle: dict | None = None
    artifact_sha256: str | None = None
    supported_pairs: set[tuple[str, str]] = field(default_factory=set)
    station_counts: dict[str, int] = field(default_factory=dict)
    metrics_table: dict | None = None
    confusion_matrix: list[list[float]] | None = None
    metrics_match_reference: bool = False
    classifier_params: dict | None = None
    package_versions: dict[str, str] = field(default_factory=dict)

    def positive_probabilities(self, frame) -> list[float]:
        if not self.ready or self.bundle is None:
            raise RuntimeError("model is not ready")
        pipeline = self.bundle["pipeline"]
        classes = [int(label) for label in pipeline.named_steps["classifier"].classes_]
        if 1 not in classes:
            raise RuntimeError("classifier has no positive class")
        with _predict_slots:
            probabilities = pipeline.predict_proba(frame)
        return [float(value) for value in probabilities[:, classes.index(1)]]

    def positive_probability(self, frame) -> float:
        return self.positive_probabilities(frame)[0]


_runtime = ModelRuntime()


def get_runtime() -> ModelRuntime:
    return _runtime


def load_runtime(settings: Settings | None = None) -> ModelRuntime:
    global _runtime
    settings = settings or get_settings()
    runtime = ModelRuntime()
    try:
        _prepare_files(settings)
        problems = _version_problems(settings)
        runtime.package_versions = _installed_versions()
        if problems:
            runtime.reason = " ".join(problems)
            _runtime = runtime
            return runtime
        artifact = settings.resolve_backend_path(settings.artifact_path)
        if not artifact.is_file():
            runtime.reason = "The saved model file is not available to the server."
            _runtime = runtime
            return runtime
        runtime.artifact_sha256 = _sha256(artifact)
        import joblib

        bundle = joblib.load(artifact)
        contract_problems = _contract_problems(bundle)
        if contract_problems:
            runtime.reason = "The saved model does not match the expected contract: " + "; ".join(contract_problems)
            _runtime = runtime
            return runtime
        runtime.bundle = bundle
        history = bundle["history"]
        runtime.supported_pairs = {
            (str(station), str(port))
            for station, port in zip(history["Station Name"], history["Port Type"])
            if pd_notna(station) and pd_notna(port)
        }
        counts = history.groupby("Station Name").size()
        runtime.station_counts = {str(key): int(value) for key, value in counts.items()}
        runtime.metrics_table = _frame_table(bundle["test_comparison"])
        runtime.confusion_matrix = _matrix(bundle["test_confusion_matrix"])
        runtime.classifier_params = _classifier_params(bundle["pipeline"])
        runtime.metrics_match_reference = _matches_reference(
            bundle["test_comparison"], runtime.confusion_matrix, runtime.classifier_params
        )
        runtime.ready = True
        runtime.reason = None
        logger.info(
            "Historical model ready. metrics_match=%s comparison_index=%s comparison_columns=%s",
            runtime.metrics_match_reference,
            runtime.metrics_table.get("index") if runtime.metrics_table else None,
            runtime.metrics_table.get("columns") if runtime.metrics_table else None,
        )
    except Exception as exc:
        logger.exception("Historical model failed to load")
        runtime.ready = False
        runtime.reason = f"The saved model could not be loaded ({type(exc).__name__})."
        runtime.bundle = None
    _runtime = runtime
    return runtime


def _prepare_files(settings: Settings) -> None:
    artifact = settings.resolve_backend_path(settings.artifact_path)
    manifest = settings.resolve_backend_path(settings.environment_manifest_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    source_model = project_root() / "ev_charger_bundle.joblib"
    source_manifest = project_root() / "model_environment.json"
    if not artifact.exists() and source_model.is_file():
        shutil.copy2(source_model, artifact)
    if not manifest.exists() and source_manifest.is_file():
        shutil.copy2(source_manifest, manifest)


def _installed_versions() -> dict[str, str]:
    import joblib
    import numpy
    import pandas
    import scipy
    import sklearn
    import threadpoolctl

    return {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "scikit-learn": sklearn.__version__,
        "pandas": pandas.__version__,
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
        "threadpoolctl": threadpoolctl.__version__,
    }


def _version_problems(settings: Settings) -> list[str]:
    manifest_path = settings.resolve_backend_path(settings.environment_manifest_path)
    if not manifest_path.is_file():
        return ["The recorded model environment file is missing."]
    recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    installed = _installed_versions()
    problems = []
    expected_python = str(recorded.get("python", ""))
    if installed["python"] != expected_python:
        problems.append(
            f"Python is {installed['python']} and the recorded environment requires {expected_python}."
        )
    packages = recorded.get("packages", {})
    for name, expected in packages.items():
        actual = installed.get(name)
        if actual != expected:
            problems.append(f"{name} is {actual or 'not installed'} and the recorded environment requires {expected}.")
    return problems


def _contract_problems(bundle: dict) -> list[str]:
    problems = []
    if not isinstance(bundle, dict):
        return ["the artifact is not a dictionary"]
    expected = {
        "schema_version": 1,
        "model_name": "Random Forest",
        "warning_cutoff": 0.17,
        "noncharging_threshold_minutes": 30,
        "history_window_days": 30,
        "exclude_arrival_day": True,
        "timezone": "America/Los_Angeles",
        "validation_year": 2019,
        "test_year": 2020,
    }
    for key, value in expected.items():
        if bundle.get(key) != value:
            problems.append(f"{key} is {bundle.get(key)!r}, expected {value!r}")
    columns = list(bundle.get("feature_columns", []))
    if columns != EXPECTED_FEATURE_COLUMNS:
        problems.append("feature_columns do not match the seven expected raw inputs")
    pipeline = bundle.get("pipeline")
    step_names = []
    if hasattr(pipeline, "steps"):
        step_names = [name for name, _step in pipeline.steps]
    if step_names[:2] != ["preprocessor", "classifier"]:
        problems.append("pipeline steps are not preprocessor then classifier")
    history = bundle.get("history")
    if history is None or any(column not in getattr(history, "columns", []) for column in EXPECTED_HISTORY_COLUMNS):
        problems.append("history is missing the expected columns")
    if "test_comparison" not in bundle or "test_confusion_matrix" not in bundle:
        problems.append("stored evaluation objects are missing")
    return problems


def _classifier_params(pipeline) -> dict:
    classifier = pipeline.named_steps["classifier"]
    return {
        "n_estimators": getattr(classifier, "n_estimators", None),
        "max_depth": getattr(classifier, "max_depth", None),
        "min_samples_leaf": getattr(classifier, "min_samples_leaf", None),
        "random_state": getattr(classifier, "random_state", None),
    }


def _matches_reference(comparison, matrix: list[list[float]] | None, params: dict | None) -> bool:
    if matrix is None or len(matrix) != 2 or any(len(row) != 2 for row in matrix):
        return False
    if [[int(round(value)) for value in row] for row in matrix] != REFERENCE_MATRIX:
        return False
    if params != REFERENCE_PARAMS:
        return False
    found = _metric_map(comparison)
    for name, expected in REFERENCE_METRICS.items():
        actual = found.get(name)
        if actual is None or abs(actual - expected) > 0.005:
            return False
    return True


def _metric_map(comparison) -> dict[str, float]:
    """Read metric values from the Random Forest column, whatever the row labels are."""
    frame = comparison
    columns = [str(column) for column in frame.columns]
    chosen = None
    for column in frame.columns:
        label = str(column).lower()
        if "random" in label or label == "model":
            chosen = column
            break
    if chosen is None and len(columns) == 1:
        chosen = frame.columns[0]
    if chosen is None:
        # Prefer the column whose precision-like value is nearest the reference.
        for column in frame.columns:
            values = [float(value) for value in frame[column].tolist() if _is_number(value)]
            if any(abs(value - 0.1443) < 0.02 for value in values):
                chosen = column
                break
    if chosen is None:
        return {}
    found: dict[str, float] = {}
    for index, value in frame[chosen].items():
        if not _is_number(value):
            continue
        label = str(index).strip().lower().replace(" ", "_").replace("-", "_")
        number = float(value)
        if "average_precision" in label or label in {"ap", "avg_precision"}:
            found["average_precision"] = number
        elif "roc" in label or "auc" in label:
            found["roc_auc"] = number
        elif label in {"f1", "f1_score"} or label.startswith("f1"):
            found["f1"] = number
        elif "precision" in label and "average" not in label:
            found["precision"] = number
        elif "recall" in label:
            found["recall"] = number
    return found


def _frame_table(frame) -> dict:
    values = []
    for row in frame.itertuples(index=False, name=None):
        values.append([None if _is_missing(item) else _json_number(item) for item in row])
    return {
        "index": [str(item) for item in frame.index],
        "columns": [str(item) for item in frame.columns],
        "values": values,
    }


def _matrix(value) -> list[list[float]]:
    array = np.asarray(value, dtype=float)
    return array.tolist()


def _sha256(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_number(value) -> bool:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return False
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_missing(value) -> bool:
    try:
        return value is None or (not isinstance(value, str) and np.isnan(value))
    except TypeError:
        return False


def _json_number(value):
    if isinstance(value, str):
        return value
    if _is_number(value):
        number = float(value)
        if number.is_integer() and abs(number) < 1_000_000_000:
            return int(number)
        return number
    return str(value)


def pd_notna(value) -> bool:
    import pandas as pd

    return not pd.isna(value)
