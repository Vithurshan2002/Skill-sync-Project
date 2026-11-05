import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


DATA_PATH = "data/service_requests.csv"
MODEL_PATH = "models/nlp_svm.joblib"


def main():
    df = pd.read_csv(DATA_PATH)

    df = df.dropna(subset=["text", "category"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df = df.drop_duplicates()

    if df["category"].nunique() < 2:
        raise ValueError("The dataset must contain at least two service categories.")

    X = df["text"]
    y = df["category"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2)
            )
        ),
        (
            "classifier",
            LinearSVC(C=1.0)
        )
    ])

    print("Training TF-IDF + SVM...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("\nAccuracy:", accuracy_score(y_test, predictions))
    print("\nClassification Report:")
    print(classification_report(y_test, predictions, zero_division=0))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nSaved model to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
