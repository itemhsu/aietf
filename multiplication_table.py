def generate_table():
    results = []
    for i in range(1, 10):
        row = []
        for j in range(1, 10):
            row.append((i, j, i * j))
        results.append(row)
    return results

if __name__ == "__main__":
    table = generate_table()
    for row in table:
        line = "  ".join(f"{i}×{j}={i*j:2d}" for i, j, _ in row)
        print(line)
