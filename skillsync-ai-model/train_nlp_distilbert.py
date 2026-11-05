import os
import json
import numpy as np
import pandas as pd

from datasets import Dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)


DATA_PATH = "data/service_requests.csv"
BASE_MODEL = "distilbert-base-uncased"
SAVE_DIR = "models/nlp_distilbert"


def main():
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["text", "category"]).drop_duplicates().copy()

    categories = sorted(df["category"].unique())
    label2id = {category: index for index, category in enumerate(categories)}
    id2label = {index: category for category, index in label2id.items()}

    df["label"] = df["category"].map(label2id)

    train_df, test_df = train_test_split(
        df,
        test_size=0.20,
        random_state=42,
        stratify=df["label"]
    )

    train_dataset = Dataset.from_pandas(
        train_df[["text", "label"]],
        preserve_index=False
    )
    test_dataset = Dataset.from_pandas(
        test_df[["text", "label"]],
        preserve_index=False
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    def tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=128
        )

    train_dataset = train_dataset.map(tokenize, batched=True)
    test_dataset = test_dataset.map(tokenize, batched=True)

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(categories),
        id2label=id2label,
        label2id=label2id
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)

        accuracy = accuracy_score(labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels,
            predictions,
            average="weighted",
            zero_division=0
        )

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    training_args = TrainingArguments(
        output_dir="models/distilbert_training",
        num_train_epochs=3,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        learning_rate=2e-5,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        processing_class=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics
    )

    trainer.train()
    results = trainer.evaluate()
    print("\nDistilBERT Results:")
    print(results)

    os.makedirs(SAVE_DIR, exist_ok=True)
    trainer.save_model(SAVE_DIR)
    tokenizer.save_pretrained(SAVE_DIR)

    with open(f"{SAVE_DIR}/labels.json", "w", encoding="utf-8") as file:
        json.dump(label2id, file, indent=4)

    print(f"\nSaved DistilBERT model to: {SAVE_DIR}")


if __name__ == "__main__":
    main()
