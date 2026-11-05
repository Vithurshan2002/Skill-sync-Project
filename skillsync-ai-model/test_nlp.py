import joblib

MODEL_PATH = "models/nlp_svm.joblib"


def main():
    model = joblib.load(MODEL_PATH)

    while True:
        text = input("\nEnter service request (or 'exit'): ").strip()

        if text.lower() == "exit":
            break

        prediction = model.predict([text])[0]
        print("Predicted category:", prediction)


if __name__ == "__main__":
    main()
