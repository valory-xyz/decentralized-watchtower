# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2022 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------
# pylint: disable=import-error

"""Watchtower Contracts Docker image."""
import logging
import time
from pathlib import Path
from typing import List

import docker
import requests
from aea.exceptions import enforce
from aea_test_autonomy.docker.base import DockerImage
from docker.models.containers import Container

from packages.valory.agents.decentralized_watchtower import PACKAGE_DIR

DEFAULT_HARDHAT_ADDR = "http://127.0.0.1"
DEFAULT_HARDHAT_PORT = 8545


class ComposableCowDockerImage(DockerImage):
    """Spawn a local network with ComposableCow deployed."""

    _CONTAINER_PORT = DEFAULT_HARDHAT_PORT

    def __init__(
        self,
        client: docker.DockerClient,
        addr: str = DEFAULT_HARDHAT_ADDR,
        port: int = DEFAULT_HARDHAT_PORT,
    ) -> None:
        """
        Initializes an instance.

        :param client: the docker client instance.
        :param addr: the host to run the network on, localhost by default.
        :param port: the port to run the network on, 8545 by default.
        """
        super().__init__(client)
        self.addr = addr
        self.port = port

    def create_many(self, nb_containers: int) -> List[Container]:
        """Instantiate the image in many containers, parametrized."""
        raise NotImplementedError()

    @property
    def image(self) -> str:
        """Get the image."""
        return "valory/composable-cow:latest"

    def create(self) -> Container:
        """Create the container."""
        ports = {f"{self._CONTAINER_PORT}/tcp": ("0.0.0.0", self.port)}  # nosec
        container = self._client.containers.run(
            self.image,
            detach=True,
            ports=ports,
            extra_hosts={"host.docker.internal": "host-gateway"},
        )
        return container

    def wait(self, max_attempts: int = 15, sleep_rate: float = 1.0) -> bool:
        """
        Wait until the image is running.

        :param max_attempts: max number of attempts.
        :param sleep_rate: the amount of time to sleep between different requests.
        :return: True if the wait was successful, False otherwise.
        """
        for i in range(max_attempts):
            try:
                response = requests.get(f"{self.addr}:{self.port}")
                enforce(response.status_code == 400, "")
                return True
            except Exception as e:  # pylint: disable=broad-except
                logging.error("Exception: %s: %s", type(e).__name__, str(e))
                logging.info(
                    "Attempt %s failed. Retrying in %s seconds...", i, sleep_rate
                )
                time.sleep(sleep_rate)
        return False



DEFAULT_JSON_SERVER_ADDR = "http://127.0.0.1"
DEFAULT_JSON_SERVER_PORT = 3000
DEFAULT_JSON_DATA_DIR = (
    PACKAGE_DIR / "tests" / "helpers" / "data" / "json_server" / "data.json"
)


class MockFearAndGreedApi(DockerImage):
    """Spawn a JSON server to for mocking the Fear and Greed API."""

    def __init__(
        self,
        client: docker.DockerClient,
        addr: str = DEFAULT_JSON_SERVER_ADDR,
        port: int = DEFAULT_JSON_SERVER_PORT,
        json_data: Path = DEFAULT_JSON_DATA_DIR,
    ):
        """Initialize."""
        super().__init__(client)
        self.addr = addr
        self.port = port
        self.json_data = json_data

    def create_many(self, nb_containers: int) -> List[Container]:
        """Instantiate the image in many containers, parametrized."""
        raise NotImplementedError()

    @property
    def image(self) -> str:
        """Get the image."""
        return "ajoelpod/mock-json-server:latest"

    def create(self) -> Container:
        """Create the container."""
        data = "/usr/src/app/data.json"
        volumes = {
            str(self.json_data): {
                "bind": data,
                "mode": "rw",
            },
        }
        ports = {"8000/tcp": ("0.0.0.0", self.port)}  # nosec
        container = self._client.containers.run(
            self.image,
            detach=True,
            ports=ports,
            volumes=volumes,
            extra_hosts={"host.docker.internal": "host-gateway"},
        )
        return container

    def wait(self, max_attempts: int = 15, sleep_rate: float = 1.0) -> bool:
        """
        Wait until the image is running.

        :param max_attempts: max number of attempts.
        :param sleep_rate: the amount of time to sleep between different requests.
        :return: True if the wait was successful, False otherwise.
        """
        for i in range(max_attempts):
            try:
                response = requests.get(f"{self.addr}:{self.port}")
                enforce(response.status_code == 200, "")
                return True
            except Exception as e:  # pylint: disable=broad-except
                logging.error("Exception: %s: %s", type(e).__name__, str(e))
                logging.info(
                    "Attempt %s failed. Retrying in %s seconds...", i, sleep_rate
                )
                time.sleep(sleep_rate)
        return False
