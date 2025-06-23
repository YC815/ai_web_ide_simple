#!/usr/bin/env python3
"""
測試正確的 unified diff 格式
這個文件展示了如何產生正確的 unified diff，避免 patch 錯誤
"""

import os
import tempfile
import subprocess


def test_diff_format():
    """測試不同的 diff 格式"""

    # 模擬的原始 HTML 內容（帶行號）
    original_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Welcome My Website!</title>
</head>
<body>
    <h1 class="text-3xl font-bold underline">Welcome My Website!</h1>
</body>
</html>"""

    print("原始 HTML 內容（帶行號）:")
    for i, line in enumerate(original_html.splitlines(), 1):
        print(f"{i:2d}: {line}")

    print("\n" + "=" * 50)

    # ❌ 錯誤的 diff 格式範例（會導致 patch 失敗）
    wrong_diff = """--- index.html
+++ index.html
@@ -10,3 +10,18 @@
  <body>
+    <nav class="bg-gray-800 p-4">
+      <div class="container mx-auto">
+        <div class="flex justify-between">
+          <a href="#" class="text-white text-lg font-semibold">My Website</a>
+          <div>
+            <a href="#" class="text-gray-300 hover:text-white px-3">Home</a>
+            <a href="#" class="text-gray-300 hover:text-white px-3">About</a>
+            <a href="#" class="text-gray-300 hover:text-white px-3">Contact</a>
+          </div>
+        </div>
+      </div>
+    </nav>
+
    <h1 class="text-3xl font-bold underline">Welcome My Website!</h1>
"""

    print("❌ 錯誤的 diff 格式:")
    print("問題：")
    print("1. 缺少完整的 context lines")
    print("2. hunk header 行數計算錯誤 (@@ -10,3 +10,18 @@)")
    print("3. 缺少結尾的 context lines")
    print("4. 可能缺少結尾換行符")
    print()

    # ✅ 正確的 diff 格式範例
    correct_diff = """--- index.html
+++ index.html
@@ -7,3 +7,18 @@
 </head>
 <body>
+    <nav class="bg-gray-800 p-4">
+      <div class="container mx-auto">
+        <div class="flex justify-between">
+          <a href="#" class="text-white text-lg font-semibold">My Website</a>
+          <div>
+            <a href="#" class="text-gray-300 hover:text-white px-3">Home</a>
+            <a href="#" class="text-gray-300 hover:text-white px-3">About</a>
+            <a href="#" class="text-gray-300 hover:text-white px-3">Contact</a>
+          </div>
+        </div>
+      </div>
+    </nav>
+
     <h1 class="text-3xl font-bold underline">Welcome My Website!</h1>
 </body>
 </html>
"""

    print("✅ 正確的 diff 格式:")
    print("修正：")
    print("1. 包含完整的 context lines（</head> 和 </body>）")
    print("2. 正確的 hunk header (@@ -7,3 +7,18 @@)")
    print("   - 原始: 從第7行開始，包含3行")
    print("   - 新版: 從第7行開始，包含18行")
    print("3. 包含結尾的 context lines")
    print("4. 確保結尾有換行符")
    print()

    # 另一個簡單的修改範例
    simple_diff = """--- index.html
+++ index.html
@@ -4,3 +4,3 @@
     <meta charset="UTF-8">
-    <title>Welcome My Website!</title>
+    <title>Hello World!</title>
 </head>
"""

    print("✅ 簡單修改的正確 diff 格式:")
    print("特點：")
    print("1. 包含前後 context lines")
    print("2. 正確的行數計算 (@@ -4,3 +4,3 @@)")
    print("3. 精確的文字匹配")
    print()

    return correct_diff, simple_diff


def demonstrate_diff_calculation():
    """展示如何計算 hunk header 的行數"""

    print("🔍 Hunk Header 計算方法:")
    print("格式: @@ -start_line,original_count +start_line,new_count @@")
    print()

    # 範例：在第7行後插入導航列
    print("範例：在 <body> 後插入導航列")
    print("原始內容：")
    print("  6: </head>")
    print("  7: <body>")
    print("  8:     <h1 class=\"text-3xl font-bold underline\">Welcome My Website!</h1>")
    print("  9: </body>")
    print()

    print("修改後：")
    print("  6: </head>")
    print("  7: <body>")
    print("  8:     <nav class=\"bg-gray-800 p-4\">")
    print("  9:       <div class=\"container mx-auto\">")
    print(" 10:         <h1>Navigation</h1>")
    print(" 11:       </div>")
    print(" 12:     </nav>")
    print(" 13: ")
    print(" 14:     <h1 class=\"text-3xl font-bold underline\">Welcome My Website!</h1>")
    print(" 15: </body>")
    print()

    print("計算過程：")
    print("1. 變更起始行：第7行")
    print("2. 原始行數：3行（包含 context）")
    print("   - </head> (context)")
    print("   - <body> (context)")
    print("   - <h1>... (context)")
    print("3. 新行數：8行（包含 context）")
    print("   - </head> (context)")
    print("   - <body> (context)")
    print("   - <nav>... (新增)")
    print("   - <div>... (新增)")
    print("   - <h1>Navigation</h1> (新增)")
    print("   - </div> (新增)")
    print("   - </nav> (新增)")
    print("   - (空行) (新增)")
    print("   - <h1>... (context)")
    print()
    print("結果：@@ -7,3 +7,8 @@")


if __name__ == "__main__":
    print("=== 正確的 Unified Diff 格式測試 ===")
    print()

    test_diff_format()
    print("\n" + "=" * 50 + "\n")
    demonstrate_diff_calculation()

    print("\n" + "=" * 50)
    print("✅ 測試完成！")
    print("這些範例展示了如何正確產生 unified diff 格式")
    print("請確保 AI 遵循這些格式規則以避免 patch 錯誤")
