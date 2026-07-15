"""
Decision Tree vs Random Forest on the Iris dataset.

Trains both classifiers on the same train/test split, evaluates each with
accuracy, a confusion matrix, and a classification report, then prints a
side-by-side comparison to determine which one performed better.
"""

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report


def evaluate_model(name, model, X_test, y_test, target_names):
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=target_names)

    print(f"\n{'=' * 50}")
    print(f"{name}")
    print(f"{'=' * 50}")
    print(f"Accuracy: {accuracy:.4f}")
    print("\nConfusion Matrix:")
    print(cm)
    print("\nClassification Report:")
    print(report)

    return accuracy


def main():
    # 1. Load the dataset
    iris = load_iris()
    X, y = iris.data, iris.target
    target_names = iris.target_names

    # 2. Split into training and testing sets (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 3. Build and train the Decision Tree
    dt_model = DecisionTreeClassifier(random_state=42)
    dt_model.fit(X_train, y_train)

    # 4. Build and train the Random Forest
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)

    # 5. Evaluate both models
    dt_accuracy = evaluate_model("Decision Tree", dt_model, X_test, y_test, target_names)
    rf_accuracy = evaluate_model("Random Forest", rf_model, X_test, y_test, target_names)

    # 6. Compare and declare a winner
    print(f"\n{'=' * 50}")
    print("COMPARISON")
    print(f"{'=' * 50}")
    print(f"Decision Tree Accuracy: {dt_accuracy:.4f}")
    print(f"Random Forest Accuracy: {rf_accuracy:.4f}")

    if rf_accuracy > dt_accuracy:
        print("\nResult: Random Forest performed better.")
    elif dt_accuracy > rf_accuracy:
        print("\nResult: Decision Tree performed better.")
    else:
        print("\nResult: Both models performed equally well on this split.")


if __name__ == "__main__":
    main()