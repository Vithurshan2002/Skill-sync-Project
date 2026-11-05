import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)


DATA_PATH = "data/reliability.csv"
MODEL_PATH = "models/reliability_rf.joblib"

FEATURES = [
    "completed_jobs_before",
    "cancellation_rate_before",
    "late_rate_before",
    "avg_response_minutes_before",
    "avg_rating_before",
    "complaint_rate_before",
]

TARGET = "completed_on_time"


def main():
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=[TARGET]).copy()

    X = df[FEATURES]
    y = df[TARGET]

    if y.nunique() < 2:
        raise ValueError("Target column must contain both 0 and 1 classes.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    model = Pipeline([
        (
            "missing_values",
            SimpleImputer(strategy="median")
        ),
        (
            "random_forest",
            RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                class_weight="balanced"
            )
        )
    ])

    print("Training reliability model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    print("\nAccuracy:", accuracy_score(y_test, predictions))
    print("\nAUC:", roc_auc_score(y_test, probabilities))
    print("\nClassification Report:")
    print(classification_report(y_test, predictions, zero_division=0))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    # Only works sensibly when the real dataset is large enough.
    if len(df) >= 10:
        cv_scores = cross_val_score(
            model,
            X,
            y,
            cv=5,
            scoring="roc_auc"
        )
        print("\nCross-validation AUC scores:", cv_scores)
        print("Average CV AUC:", cv_scores.mean())

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nSaved model to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
