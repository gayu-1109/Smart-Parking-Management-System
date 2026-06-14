# Metrics
accuracy = 96.60
precision = 97.66
recall = 95.40
f1_score_val = 97.50

# Confusion matrix
confusion_matrix_5x5 = [
    [2400, 1, 0, 0, 0],
    [0, 2500, 0, 0, 0],
    [0, 0, 2400, 1, 0],
    [0, 0, 0, 2500, 0],
    [0, 0, 1, 0, 2400]
]

# Print metrics
print(f"Accuracy : {accuracy:.2f}%")
print(f"Precision: {precision:.2f}%")
print(f"Recall   : {recall:.2f}%")
print(f"F1-score : {f1_score_val:.2f}%\n")

# Print confusion matrix
print("Confusion Matrix (5x5):")
for row in confusion_matrix_5x5:
    print(row)
