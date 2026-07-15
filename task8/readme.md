
# Decision Tree vs Random Forest — Iris Dataset

Trains a `DecisionTreeClassifier` and a `RandomForestClassifier` on the
same train/test split of the Iris dataset, evaluates both with accuracy,
a confusion matrix, and a classification report, then compares them.

## What it demonstrates

- Loading a built-in scikit-learn dataset (`load_iris`)
- `train_test_split` with `stratify=y` (keeps class proportions equal in
  both the train and test sets — important for small, balanced datasets
  like Iris)
- Training two different classifier types on identical data
- Evaluating with three complementary metrics:
  - **Accuracy** — overall % of correct predictions
  - **Confusion matrix** — which classes get mixed up with which
  - **Classification report** — precision/recall/F1 per class

## Files

| File                    | Purpose                        |
|--------------------------|----------------------------------|
| `iris_classifiers.py`   | Main script — run this          |
| `requirements.txt`      | Python dependencies             |

## Setup

1. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

## Usage

```
python iris_classifiers.py
```

## Example output (yours may vary slightly by scikit-learn version)

```
Decision Tree Accuracy: 0.9333
Random Forest Accuracy: 0.9000

Result: Decision Tree performed better.
```

## Why results can surprise you

Random Forest usually generalizes better than a single Decision Tree on
larger or noisier datasets, because averaging many trees reduces
overfitting. But Iris is a small (150 rows), very clean, easily-separable
dataset — with so few test samples (30), a couple of misclassifications
swing the accuracy a lot, so a single well-fit Decision Tree can sometimes
edge out the Random Forest by chance on a given split. Try changing
`random_state` in `train_test_split` to see the result shift.

## Reading the confusion matrix

Rows = actual class, columns = predicted class, in the order
`[setosa, versicolor, virginica]`. Numbers on the diagonal are correct
predictions; anything off-diagonal is a mistake — e.g. a `1` in row
"versicolor", column "virginica" means one versicolor flower was
incorrectly predicted as virginica.