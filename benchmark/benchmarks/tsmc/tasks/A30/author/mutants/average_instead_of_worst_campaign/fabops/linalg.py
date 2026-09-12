"""Solve the observed correlation system without inverting missing coordinates."""
def solve(matrix, vector):
    size = len(vector)
    augmented = [list(row) + [value] for row, value in zip(matrix, vector)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a - factor*b for a, b in zip(augmented[row], augmented[column])]
    return [row[-1] for row in augmented]
