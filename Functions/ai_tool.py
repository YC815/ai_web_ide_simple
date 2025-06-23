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


def diff_code(container_name: str, diff_code: str, language: str):
    client = docker.from_env()
    container = client.containers.get(container_name)
    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".diff") as tmp:
        tmp.write(diff_code)
        diff_path = tmp.name

    try:
        container.put_archive(
            path="/tmp",
            data=create_tar_from_file(diff_path, "patch.diff")
        )

        command = f"sh -c 'cd /usr/share/nginx/{language} && patch -p1 < /tmp/patch.diff'"
        result = container.exec_run(command)

        return result.output.decode("utf-8")
    finally:
        os.remove(diff_path)
