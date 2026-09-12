"""Legacy marginal approximation ignores coupled sensor geometry."""
def solve(matrix, vector):
    return [value / matrix[index][index] for index, value in enumerate(vector)]
