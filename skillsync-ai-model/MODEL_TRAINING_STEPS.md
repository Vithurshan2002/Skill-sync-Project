# SkillSync AI: Model Training Steps

For application setup, startup and verification, see the [main SkillSync guide](../project/README.md).

This guide explains the training process implemented in this folder in simple language. It describes the code and current CSV files; it does not claim that training was run again or report new accuracy results.

## 1. Which models are used?

| Model | Purpose | Training file | Used by the current API? |
| --- | --- | --- | --- |
| TF-IDF + Linear Support Vector Machine (SVM) | Read a service request and predict its service category | `train_nlp_svm.py` | Yes |
| Random Forest | Predict the probability that a worker completes a job on time | `train_reliability.py` | Yes |
| DistilBERT (`distilbert-base-uncased`) | An alternative model for predicting the service category | `train_nlp_distilbert.py` | No; separate training and comparison workflow |
| Random Forest candidate | Train a new reliability model from recorded real booking outcomes | `train_from_outcomes.py` | Not automatically; saves a separate candidate for review |

The service categories are **Plumbing, Electrical, Carpentry, and Welding**.

## 2. Prepare the datasets

The training scripts read existing data files. They do not collect or label the initial CSV data themselves.

| Dataset | Contents | Current rows before cleaning |
| --- | --- | --- |
| `data/service_requests.csv` | Request text and its correct category | 1,200; 300 per category |
| `data/service_requests_unseen.csv` | Separate examples for comparing the text models | 80; 20 per category |
| `data/reliability.csv` | Worker history and an on-time completion label | 20; 10 labelled 1 and 10 labelled 0 |

For text classification, `text` is the input and `category` is the correct answer.

For reliability, `completed_on_time` is the answer: **1 = on time**, **0 = not on time**. The recorded-outcomes workflow uses customer-confirmed completed bookings; cancellations are history inputs, not negative completion labels.

## 3. Train the service classification model: TF-IDF + SVM

Source: `train_nlp_svm.py`.

1. **Load data:** Read `data/service_requests.csv` using pandas.
2. **Clean data:** Remove rows missing text or category, convert both columns to strings, trim surrounding spaces, and remove duplicate rows.
3. **Check categories:** Require at least two different categories.
4. **Choose inputs and answers:** Use request text as `X` and category as `y`.
5. **Split the data:** Use 80% for training and 20% for testing. Stratification keeps category proportions similar in both groups. `random_state=42` makes the split repeatable.
6. **Convert text to numbers:** TF-IDF gives words and phrases numerical weights. It lowercases text and uses single words and two-word phrases (`ngram_range=(1, 2)`).
7. **Train SVM:** Fit `LinearSVC(C=1.0)` to the training examples. TF-IDF and SVM are joined in one pipeline, so TF-IDF learns its vocabulary from the training split.
8. **Predict test categories:** Run the trained pipeline on the held-out 20%.
9. **Evaluate:** Print accuracy, a classification report containing precision/recall/F1, and a confusion matrix.
10. **Save:** Store the complete pipeline at `models/nlp_svm.joblib`.

Example purpose: classify a request such as "My kitchen sink is leaking" into a service category.

## 4. Train the worker reliability model: Random Forest

Source: `train_reliability.py`.

The model uses six history fields measured before the job outcome:

| Input field | Simple meaning |
| --- | --- |
| `completed_jobs_before` | Previous completed jobs |
| `cancellation_rate_before` | Previous worker cancellation rate |
| `late_rate_before` | Previous late completion rate |
| `avg_response_minutes_before` | Average time taken to respond |
| `avg_rating_before` | Average previous customer rating |
| `complaint_rate_before` | Previous complaint rate |

1. **Load data:** Read `data/reliability.csv`.
2. **Clean labels:** Remove rows without a `completed_on_time` value.
3. **Choose inputs and answer:** Use the six history fields as `X` and `completed_on_time` as `y`.
4. **Check classes:** Require both outcome classes for meaningful binary training; the code checks that at least two distinct target values exist.
5. **Split the data:** Make a stratified 80% training / 20% test split with `random_state=42`.
6. **Fill missing inputs:** Use `SimpleImputer(strategy="median")`. Each missing value is replaced with its column's median learned from the training split.
7. **Train Random Forest:** Fit 300 decision trees using `n_estimators=300`, `random_state=42`, and `class_weight="balanced"`. Balanced weights account for differences in class frequency.
8. **Predict:** Produce both outcome labels and the probability of class 1, meaning on-time completion.
9. **Evaluate:** Print accuracy, ROC AUC, a classification report, and a confusion matrix.
10. **Cross-validate:** If the dataset has at least 10 rows, attempt five-fold ROC AUC cross-validation on the full dataset. Each fold trains a separate pipeline; each class still needs enough examples.
11. **Save:** Store the original training-split pipeline at `models/reliability_rf.joblib`. Cross-validation does not replace it with a model fitted on all rows.

The current reliability CSV has only 20 examples, so its evaluation provides limited evidence of real-world performance.

## 5. Train the optional text model: DistilBERT

Source: `train_nlp_distilbert.py`.

DistilBERT starts from a pretrained language model and fine-tunes it for the project's service categories.

1. **Load data:** Read the same `data/service_requests.csv` used by SVM.
2. **Clean data:** Remove rows missing text/category and remove duplicate rows.
3. **Encode categories:** Sort the category names and assign each a numeric ID. Keep mappings in both directions.
4. **Split the data:** Use a stratified 80% training / 20% evaluation split with `random_state=42`.
5. **Create datasets:** Convert the text and numeric labels to Hugging Face datasets.
6. **Load the tokenizer:** Use the tokenizer for `distilbert-base-uncased`.
7. **Tokenize:** Convert text into token IDs, truncate to at most 128 tokens, and dynamically pad examples within each batch.
8. **Load the pretrained model:** Create a sequence classification model with one output per service category.
9. **Set training options:** Use the settings below.
10. **Fine-tune:** Run `Trainer.train()` for three passes through the training data.
11. **Evaluate each epoch:** Calculate accuracy and weighted precision, recall, and F1; also log progress and save a checkpoint each epoch.
12. **Select the best checkpoint:** Reload the checkpoint with the highest evaluation F1.
13. **Evaluate again:** Print the selected model's evaluation results.
14. **Save:** Write the model, tokenizer, and `labels.json` to `models/nlp_distilbert/`. Training checkpoints go to `models/distilbert_training/`.

| Setting | Value |
| --- | --- |
| Base model | `distilbert-base-uncased` |
| Epochs | 3 |
| Training batch size per device | 8 |
| Evaluation batch size per device | 8 |
| Learning rate | `2e-5` (0.00002) |
| Weight decay | 0.01 |
| Maximum token length | 128 |
| Best-model metric | Weighted F1 |

Although the script calls its held-out data `test_dataset`, it uses this data to select the best checkpoint. It therefore acts as validation data. The separate unseen dataset provides another evaluation stage.

## 6. Compare SVM and DistilBERT on unseen examples

Source: `evaluate_unseen.py`. This evaluates saved models; it does not train them.

1. Load `data/service_requests_unseen.csv`.
2. Remove rows missing text or category.
3. Load the saved SVM pipeline and predict every example's category.
4. Print SVM accuracy and its classification report.
5. Load the saved DistilBERT model and tokenizer.
6. Predict in batches of 16, with a maximum of 128 tokens, in evaluation mode with gradient calculation disabled.
7. Convert predicted numeric IDs back to category names.
8. Print DistilBERT accuracy and its classification report.
9. Save the text, actual category, and both model predictions to `unseen_test_predictions.csv`.

Both saved text models must exist. The script overwrites the predictions CSV. Keep unseen examples separate from training examples; this script does not check for overlap.

## 7. Retrain reliability using real booking outcomes

Sources: `train_from_outcomes.py` and `feature_contract.json`.

This is a separate workflow for creating a candidate model from a JSON export of real outcomes.

1. **Read the export:** Accept a dataset path, a new output directory, and optionally a baseline model path.
2. **Check the contract:** Require feature version `recorded-outcomes-v2` and target `completed_on_time`.
3. **Validate records:** Reject demo/test data, incorrect feature versions, duplicate bookings, invalid labels, and invalid feature values. Known feature values must be finite and nonnegative; rates cannot exceed 1, ratings cannot exceed 5, and job counts must be integers.
4. **Check timestamps:** Prediction and outcome timestamps must include timezones, and the outcome cannot precede the prediction snapshot.
5. **Require enough data:** At least 100 eligible records from at least 5 workers are required.
6. **Split chronologically:** Sort by snapshot time and booking ID. Choose a cutoff near the 80% point, using earlier snapshots for training and later snapshots for testing.
7. **Prevent future-information leakage:** Remove training records whose outcomes were not known before the test period began. The final split can therefore differ from exactly 80/20.
8. **Check class counts:** Require at least 10 examples of each outcome in training and 5 of each in testing.
9. **Train a candidate:** Fit median imputation with `keep_empty_features=True`, followed by the same balanced 300-tree Random Forest.
10. **Compare with the baseline:** Load the existing reliability model and evaluate both models on the same test records.
11. **Measure performance:** Calculate accuracy, precision, recall, ROC AUC, Brier score, and five probability bands comparing predicted probabilities with actual on-time rates. Binary predictions use a 0.5 threshold.
12. **Check groups:** Report candidate performance by service category and, when present, on workers absent from the training set.
13. **Flag for review:** Set `reviewRecommended` when the candidate has a lower Brier score than the baseline. This is a review signal, not automatic deployment.
14. **Save separately:** Write `reliability_rf.joblib`, `evaluation.json`, `reliability_rf.metadata.json`, and a copy of `feature_contract.json` into the new output directory. Reports include dataset/model hashes for tracking exactly which files were used.

The active API model is unchanged by this script. The 20-row reliability CSV is not the required real-outcome JSON export.

## 8. How trained models are used

Source: `main.py`.

1. At startup, load `models/nlp_svm.joblib` and `models/reliability_rf.joblib`.
2. Use SVM to classify incoming request text.
3. Use Random Forest to predict worker reliability from history.
4. For smart recommendations, filter to available workers in the predicted service category.
5. Use the formulas in `scoring.py` to calculate scores and rank workers.

The recommendation formula combines skill (30%), reliability (30%), rating (15%), availability (10%), and distance (15%). Missing optional scoring components are excluded and the remaining weights are normalized. These weights and explanation rules are manually defined; they are not a separately trained model.

`main.py` performs predictions only. `scripts/setup_integration.py` configures the integration database and environment; it does not train models.

## 9. Commands for the training workflow

Run these from the workspace root, then work inside the AI folder:

```powershell
cd skillsync-ai-model
uv sync --locked

# Train the models loaded by the API.
uv run python train_nlp_svm.py
uv run python train_reliability.py

# Optionally train DistilBERT and compare both text models.
uv run python train_nlp_distilbert.py
uv run python evaluate_unseen.py
```

The first two training scripts overwrite their saved API model files. DistilBERT training saves to its configured model folder but does not switch the API to DistilBERT. Training is not required merely to start the application when saved models already exist.

For real-outcome retraining, supply an actual exported JSON dataset and a new candidate directory. Example:

```powershell
uv run python train_from_outcomes.py --dataset data/recorded_outcomes.json --output-dir models/candidate_001
```

`data/recorded_outcomes.json` is an example export path, not one of the existing CSV files. The candidate output directory must not already exist.

## 10. Meaning of evaluation terms

| Term | Simple meaning |
| --- | --- |
| Accuracy | Fraction of predictions that are correct |
| Precision | How often a predicted class is correct |
| Recall | How many actual examples of a class the model identifies |
| F1 | A combined measure of precision and recall |
| Confusion matrix | A table showing correct predictions and which classes were confused |
| ROC AUC | How well the model ranks positive outcomes above negative outcomes |
| Brier score | Error in predicted probabilities; lower is better |
| Calibration | Whether predicted probabilities agree with observed outcome frequencies |
| Epoch | One pass through the training examples |
| Cross-validation | Repeated training and evaluation using different held-out portions of the data |

