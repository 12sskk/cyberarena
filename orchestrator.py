"""
Shared Docker Container Orchestrator for CyberArena.
Ensures that when the first user opens a challenge, a single Docker container is built/deployed,
and all subsequent users who open that challenge share the exact same running container instance.
Includes an automatic shared local microservice fallback when the Docker daemon is offline.
"""
import os
import sys
import time
import socket
import hashlib
import threading
import subprocess
try:
    import docker
except ImportError:
    docker = None
from challenges_registry import CHALLENGES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex(("127.0.0.1", port)) == 0


class SharedDockerOrchestrator:
    def __init__(self):
        self.locks = {cid: threading.Lock() for cid in CHALLENGES}
        self.instances = {}  # cid -> dict of metadata
        self.docker_client = None
        self.docker_mode = False
        self._init_docker()

    def _init_docker(self):
        try:
            client = docker.from_env()
            client.ping()
            self.docker_client = client
            self.docker_mode = True
        except Exception:
            self.docker_client = None
            self.docker_mode = False

    def get_engine_info(self) -> dict:
        self._init_docker()
        return {
            "docker_daemon_connected": self.docker_mode,
            "mode_label": "Docker Engine (Shared Sibling Containers)" if self.docker_mode else "Containerized Shared Runtime (Local Daemon Fallback)",
            "active_containers": sum(1 for cid in CHALLENGES if self.get_status(cid)["running"])
        }

    def get_status(self, challenge_id: str) -> dict:
        chall = CHALLENGES[challenge_id]
        inst = self.instances.get(challenge_id)

        if self.docker_mode and self.docker_client:
            try:
                c = self.docker_client.containers.get(chall["container_name"])
                if c.status == "running":
                    ports = c.attrs.get("NetworkSettings", {}).get("Ports", {}).get("5000/tcp")
                    host_port = int(ports[0]["HostPort"]) if ports else chall["port"]
                    if not inst:
                        inst = {
                            "container_id": c.short_id,
                            "port": host_port,
                            "started_at": time.time(),
                            "deployed_by": "docker-daemon",
                            "operators": set(),
                            "mode": "docker"
                        }
                        self.instances[challenge_id] = inst
                    return {
                        "running": True,
                        "container_id": c.short_id,
                        "container_name": chall["container_name"],
                        "port": host_port,
                        "uptime": int(time.time() - inst["started_at"]),
                        "deployed_by": inst["deployed_by"],
                        "operators": sorted(list(inst["operators"])),
                        "operator_count": len(inst["operators"]),
                        "mode": "docker"
                    }
            except Exception:
                pass

        # Check fallback shared process instance
        if inst and inst.get("mode") == "shared-process":
            proc = inst.get("proc")
            if proc and proc.poll() is None:
                return {
                    "running": True,
                    "container_id": inst["container_id"],
                    "container_name": chall["container_name"],
                    "port": inst["port"],
                    "uptime": int(time.time() - inst["started_at"]),
                    "deployed_by": inst["deployed_by"],
                    "operators": sorted(list(inst["operators"])),
                    "operator_count": len(inst["operators"]),
                    "mode": "shared-container-runtime"
                }

        return {
            "running": False,
            "container_id": None,
            "container_name": chall["container_name"],
            "port": chall["port"],
            "uptime": 0,
            "deployed_by": None,
            "operators": [],
            "operator_count": 0,
            "mode": "standby"
        }

    def deploy_or_join(self, challenge_id: str, username: str) -> dict:
        """
        If the challenge container is not running, deploys it once.
        If it is already running, attaches the user to the existing shared container.
        """
        chall = CHALLENGES.get(challenge_id)
        if not chall:
            raise ValueError("Unknown challenge_id")

        with self.locks[challenge_id]:
            current = self.get_status(challenge_id)
            if current["running"]:
                # Container already deployed by an earlier user! Share it!
                self.instances[challenge_id]["operators"].add(username)
                self.instances[challenge_id]["last_active"] = time.time()
                updated = self.get_status(challenge_id)
                updated["action_taken"] = "JOINED_EXISTING_SHARED_CONTAINER"
                return updated

            # First user to open this challenge -> Deploy shared container now
            self._init_docker()
            if self.docker_mode and self.docker_client:
                return self._deploy_docker_container(challenge_id, username)
            else:
                return self._deploy_shared_runtime_process(challenge_id, username)

    def _deploy_docker_container(self, challenge_id: str, username: str) -> dict:
        chall = CHALLENGES[challenge_id]
        image_tag = chall["image"]
        container_name = chall["container_name"]
        context_dir = os.path.join(BASE_DIR, "challenges", challenge_id)

        # 1. Ensure image is built from challenges/<challenge_id>/Dockerfile
        images = [tag for img in self.docker_client.images.list() for tag in img.tags]
        if image_tag not in images:
            self.docker_client.images.build(path=context_dir, tag=image_tag, rm=True)

        # 2. Remove any stopped container with the same shared name
        try:
            old = self.docker_client.containers.get(container_name)
            if old.status != "running":
                old.remove(force=True)
        except Exception:
            pass

        # 3. Start the single shared container for this challenge
        container = self.docker_client.containers.run(
            image_tag,
            name=container_name,
            detach=True,
            ports={"5000/tcp": chall["port"]},
            labels={
                "cyberarena.shared": "true",
                "cyberarena.challenge_id": challenge_id,
                "cyberarena.deployed_by": username
            },
            mem_limit="128m"
        )
        container.reload()
        ports = container.attrs["NetworkSettings"]["Ports"]["5000/tcp"]
        host_port = int(ports[0]["HostPort"]) if ports else chall["port"]

        self.instances[challenge_id] = {
            "container_id": container.short_id,
            "port": host_port,
            "started_at": time.time(),
            "last_active": time.time(),
            "deployed_by": username,
            "operators": {username},
            "mode": "docker"
        }
        status = self.get_status(challenge_id)
        status["action_taken"] = "DEPLOYED_NEW_SHARED_CONTAINER"
        return status

    def _deploy_shared_runtime_process(self, challenge_id: str, username: str) -> dict:
        chall = CHALLENGES[challenge_id]
        port = chall["port"]
        script_path = os.path.join(BASE_DIR, "challenges", challenge_id, "app.py")

        env = os.environ.copy()
        env["CHALLENGE_ID"] = challenge_id
        env["PORT"] = str(port)

        proc = subprocess.Popen(
            [sys.executable, script_path],
            cwd=os.path.join(BASE_DIR, "challenges", challenge_id),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Wait up to 3 seconds for the shared container port to bind
        for _ in range(15):
            if is_port_open(port):
                break
            time.sleep(0.15)

        cid_hash = hashlib.sha256(f"{challenge_id}-{proc.pid}".encode()).hexdigest()[:12]
        self.instances[challenge_id] = {
            "container_id": cid_hash,
            "port": port,
            "started_at": time.time(),
            "last_active": time.time(),
            "deployed_by": username,
            "operators": {username},
            "mode": "shared-process",
            "proc": proc
        }
        status = self.get_status(challenge_id)
        status["action_taken"] = "DEPLOYED_NEW_SHARED_CONTAINER"
        return status

    def reset_shared_container(self, challenge_id: str, username: str) -> dict:
        """Stops the shared container and redeploys a fresh shared instance."""
        self.stop_shared_container(challenge_id)
        return self.deploy_or_join(challenge_id, username)

    def stop_shared_container(self, challenge_id: str) -> bool:
        chall = CHALLENGES.get(challenge_id)
        if not chall:
            return False
        with self.locks[challenge_id]:
            if self.docker_mode and self.docker_client:
                try:
                    c = self.docker_client.containers.get(chall["container_name"])
                    c.remove(force=True)
                except Exception:
                    pass
            inst = self.instances.pop(challenge_id, None)
            if inst and inst.get("proc"):
                try:
                    inst["proc"].terminate()
                    inst["proc"].wait(timeout=2)
                except Exception:
                    pass
            return True
