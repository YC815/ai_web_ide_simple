import os
import docker
import shutil
import socket

client = docker.from_env()


def get_containers():
    containers = client.containers.list(all=True)
    container_list = []
    for container in containers:
        container_list.append(container.name, container.status, container.id, "\n")
    return container_list


def find_available_port(start_port=8080):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                port += 1


def create_container(container_name: str, port: int = 8080):
    client = docker.from_env()

    # 找可用的 port
    port = find_available_port(port)

    # 建立專案資料夾
    template_dir = "./docker_template"
    project_dir = f"./ai-web-ide_{container_name}"
    os.makedirs(project_dir, exist_ok=True)

    # 複製模板檔案
    for filename in ["index.html", "index.css", "index.js"]:
        shutil.copy(os.path.join(template_dir, filename), os.path.join(project_dir, filename))

    # 建立 Dockerfile
    dockerfile_path = os.path.join(project_dir, "Dockerfile")
    with open(dockerfile_path, "w") as f:
        f.write("""
FROM nginx:alpine
COPY . /usr/share/nginx/html
        """.strip())

    # 建立 image
    image_tag = f"ai-web-ide/{container_name.lower()}_image"
    print(f"📦 Building image {image_tag}...")
    client.images.build(path=project_dir, tag=image_tag)

    # 停用並移除舊容器（若已存在）
    container_id = f"{container_name.lower()}_container"
    try:
        existing_container = client.containers.get(container_id)
        print(f"⚠️ Stopping and removing existing container {container_id}...")
        existing_container.stop()
        existing_container.remove()
    except docker.errors.NotFound:
        pass

    # 啟動容器
    print(f"🚀 Starting container {container_id} on port {port}...")
    container = client.containers.run(
        image_tag,
        name=container_id,
        ports={"80/tcp": port},
        detach=True
    )

    print(f"✅ {container_id} is running at http://localhost:{port}")
    return container
