import numpy as np

# Define the coefficients matrix and the result vector
coefficients = np.array([[1, 1, 0, 0],
                         [1, 0, 1, 0],
                         [0, 1, 1, 0],
                         [1, 0, 0, 1],
                         [0, 1, 0, 1]])

result = np.array([10, 13, 7, 15, 10])

result = np.dot(coefficients.T, result)
coefficients = np.dot(coefficients.T, coefficients)
print(result)
print(coefficients)

solution = np.linalg.lstsq(coefficients, result, rcond=None)[0]

print("Solution:")
print(solution)
# Solve the system of equations
# solution = np.linalg.solve(coefficients, result)

# print("Solution:")
# print(solution)

x = 5

def blah(x):
    return x+3

blah(7)
print(x)