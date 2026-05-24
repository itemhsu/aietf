import datetime
import sys
import platform

def hello():
    return "Hello, World!"

def run_tests():
    results = []

    # Test 1: Basic hello
    result = hello()
    results.append({
        "name": "test_hello_returns_string",
        "status": "PASS" if isinstance(result, str) else "FAIL",
        "output": result
    })

    # Test 2: Content check
    results.append({
        "name": "test_hello_content",
        "status": "PASS" if result == "Hello, World!" else "FAIL",
        "output": f"Expected 'Hello, World!', got '{result}'"
    })

    # Test 3: Length check
    results.append({
        "name": "test_hello_length",
        "status": "PASS" if len(result) == 13 else "FAIL",
        "output": f"Length = {len(result)}"
    })

    return results

if __name__ == "__main__":
    print("=== Hello Test Runner ===")
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Time: {datetime.datetime.now()}")
    print()

    results = run_tests()
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)

    for r in results:
        icon = "✓" if r["status"] == "PASS" else "✗"
        print(f"  [{icon}] {r['name']}: {r['output']}")

    print()
    print(f"Result: {passed}/{total} tests passed")
