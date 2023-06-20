# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
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

"""The e2e fixtures."""
import logging
from typing import Generator

import docker
import pytest
from aea_test_autonomy.docker.base import launch_image

from packages.valory.agents.decentralized_watchtower.tests.helpers.docker import (
    ComposableCowDockerImage,
    DEFAULT_HARDHAT_ADDR,
    DEFAULT_HARDHAT_PORT,
    DEFAULT_JSON_SERVER_ADDR,
    DEFAULT_JSON_SERVER_PORT,
    MockFearAndGreedApi,
)


@pytest.mark.integration
class UseHardHatWatchtowerBaseTest:  # pylint: disable=too-few-public-methods
    """Inherit from this class to use HardHat local net with the Watchtower related contracts deployed."""

    NETWORK_ADDRESS = DEFAULT_HARDHAT_ADDR
    NETWORK_PORT = DEFAULT_HARDHAT_PORT

    @classmethod
    @pytest.fixture(autouse=True)
    def _start_network(
        cls,
        timeout: int = 3,
        max_attempts: int = 200,
    ) -> Generator:
        """Start a HardHat instance."""
        client = docker.from_env()
        logging.info(
            f"Launching the network on port {cls.NETWORK_ADDRESS}"
        )
        image = ComposableCowDockerImage(
            client,
            addr=cls.NETWORK_ADDRESS,
            port=cls.NETWORK_PORT,
        )
        yield from launch_image(image, timeout=timeout, max_attempts=max_attempts)


@pytest.mark.integration
class UseMockApiBaseTest:  # pylint: disable=too-few-public-methods
    """Inherit from this class to use a mock Orders API."""

    MOCK_API_ADDRESS = DEFAULT_JSON_SERVER_ADDR
    MOCK_API_PORT = DEFAULT_JSON_SERVER_PORT

    @classmethod
    @pytest.fixture(autouse=True)
    def _start_mock_api(
        cls,
        timeout: int = 3,
        max_attempts: int = 200,
    ) -> Generator:
        """Start a Orders API instance."""
        client = docker.from_env()
        logging.info(f"Launching the Orders API on port {cls.MOCK_API_PORT}")
        image = MockFearAndGreedApi(
            client,
            addr=cls.MOCK_API_ADDRESS,
            port=cls.MOCK_API_PORT,
        )
        yield from launch_image(image, timeout=timeout, max_attempts=max_attempts)
