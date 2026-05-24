# aietf

Python 練習專案，包含基礎程式範例與 HTML 視覺化結果展示。

## 專案內容

| 檔案 | 說明 |
|------|------|
| `hello_test.py` | Hello World 單元測試（3 個測試案例） |
| `hello_result.html` | Hello 測試執行結果 HTML 展示 |
| `multiplication_table.py` | 九九乘法表產生器 |
| `multiplication_result.html` | 九九乘法表互動式 HTML 展示 |

## 執行方式

```bash
# Hello 測試
python3 hello_test.py

# 九九乘法表
python3 multiplication_table.py
```

## 執行環境

- Python 3.9+
- 無需額外套件

## 範例輸出

### Hello 測試
```
=== Hello Test Runner ===
  [✓] test_hello_returns_string: Hello, World!
  [✓] test_hello_content: Expected 'Hello, World!', got 'Hello, World!'
  [✓] test_hello_length: Length = 13

Result: 3/3 tests passed
```

### 九九乘法表
```
1×1= 1  1×2= 2  ...  1×9= 9
2×1= 2  2×2= 4  ...  2×9=18
...
9×1= 9  9×2=18  ...  9×9=81
```
