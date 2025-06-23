import docker
import tempfile
import os

import tarfile
import io


def get_html_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.html")
    return result.output.decode("utf-8")


def get_js_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.js")
    return result.output.decode("utf-8")


def get_css_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.css")
    return result.output.decode("utf-8")


def create_tar_from_file(filepath: str, arcname: str) -> bytes:
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tar.add(filepath, arcname=arcname)
    tar_stream.seek(0)
    return tar_stream.read()


def diff_code(container_name: str, diff_code: str, language: str) -> str:
    client = docker.from_env()
    container = client.containers.get(container_name)

    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".diff") as tmp:
        tmp.write(diff_code)
        diff_path = tmp.name

    try:
        # 上傳 patch.diff 到 /tmp 位置
        container.put_archive(
            path="/tmp",
            data=create_tar_from_file(diff_path, "patch.diff")
        )

        # Dry-run 模擬是否能成功套用（使用 --batch --forward）
        dry_run_cmd = f"sh -c 'cd /usr/share/nginx/{language} && patch --dry-run --batch --forward -p1 < /tmp/patch.diff'"
        dry_run_result = container.exec_run(dry_run_cmd)

        if dry_run_result.exit_code != 0:
            return "[❌ PATCH FAILED]\n" + dry_run_result.output.decode("utf-8").strip()

        # 實際執行 patch
        apply_cmd = f"sh -c 'cd /usr/share/nginx/{language} && patch --batch --forward -p1 < /tmp/patch.diff'"
        apply_result = container.exec_run(apply_cmd)

        return "[✅ PATCH APPLIED]\n" + apply_result.output.decode("utf-8").strip()

    finally:
        os.remove(diff_path)
