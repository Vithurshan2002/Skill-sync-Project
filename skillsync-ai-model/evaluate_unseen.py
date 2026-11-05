import joblib
import pandas as pd
import torch

from sklearn.metrics import accuracy_score, classification_report
from transformers import AutoTokenizer, AutoModelForSequenceClassification

TEST_PATH = "data/service_requests_unseen.csv"
SVM_MODEL_PATH = "models/nlp_svm.joblib"
DISTILBERT_PATH = "models/nlp_distilbert"

# -----------------------------
# 1. Load unseen test data
# -----------------------------
df = pd.read_csv(TEST_PATH)
df = df.dropna(subset=["text", "category"]).copy()

texts = df["text"].astype(str).tolist()
y_true = df["category"].astype(str).tolist()

print(f"Loaded {len(df)} unseen test examples.")

# -----------------------------
# 2. Evaluate TF-IDF + SVM
# -----------------------------
svm_model = joblib.load(SVM_MODEL_PATH)
svm_predictions = svm_model.predict(texts)

print("\n==============================")
print("TF-IDF + SVM")
print("==============================")
print("Accuracy:", accuracy_score(y_true, svm_predictions))
print(
    classification_report(
        y_true,
        svm_predictions,
        digits=4,
        zero_division=0
    )
)

# -----------------------------
# 3. Load DistilBERT
# -----------------------------
tokenizer = AutoTokenizer.from_pretrained(DISTILBERT_PATH)
bert_model = AutoModelForSequenceClassification.from_pretrained(DISTILBERT_PATH)
bert_model.eval()

# -----------------------------
# 4. Predict with DistilBERT
# -----------------------------
bert_predictions = []
batch_size = 16

for start in range(0, len(texts), batch_size):
    batch_texts = texts[start:start + batch_size]

    inputs = tokenizer(
        batch_texts,
        padding=True,
        truncation=True,
        max_length=128,
        return_tensors="pt"
    )

    with torch.no_grad():
        outputs = bert_model(**inputs)

    prediction_ids = outputs.logits.argmax(dim=-1).tolist()

    for label_id in prediction_ids:
        bert_predictions.append(
            bert_model.config.id2label[label_id]
        )

print("\n==============================")
print("DistilBERT")
print("==============================")
print("Accuracy:", accuracy_score(y_true, bert_predictions))
print(
    classification_report(
        y_true,
        bert_predictions,
        digits=4,
        zero_division=0
    )
)

# -----------------------------
# 5. Save detailed predictions
# -----------------------------
results = pd.DataFrame({
    "text": texts,
    "actual": y_true,
    "svm_prediction": svm_predictions,
    "distilbert_prediction": bert_predictions
})

results.to_csv(
    "unseen_test_predictions.csv",
    index=False
)

print("\nSaved detailed predictions to unseen_test_predictions.csv")
