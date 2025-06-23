import os
import tempfile
import subprocess


def diff_code_local(target_folder: str, diff_code: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".diff") as tmp:
        tmp.write(diff_code)
        diff_path = tmp.name

    try:
        # dry-run 加上 --forward，如果 diff 不吻合會回傳錯誤
        dry_run = subprocess.run(
            ["patch", "--dry-run", "--batch", "--forward", "-p0", "-d", target_folder, "-i", diff_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if dry_run.returncode != 0:
            return "[❌ PATCH FAILED]\n" + dry_run.stdout.strip()

        result = subprocess.run(
            ["patch", "--batch", "--forward", "-p0", "-d", target_folder, "-i", diff_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return "[✅ PATCH APPLIED]\n" + result.stdout.strip()

    finally:
        os.remove(diff_path)


diff = """\
--- test.html
+++ test.html
@@ -1 +1 @@
-<h1>Hello</h1>
+<h1>Hi there</h1>
"""

output = diff_code_local("tests", diff)
print(output)
