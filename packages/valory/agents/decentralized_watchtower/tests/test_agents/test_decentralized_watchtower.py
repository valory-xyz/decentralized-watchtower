# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2023 Valory AG
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
# pylint: skip-file
# mypy: ignore-errors
# flake8: noqa

"""End-to-End tests for the balancer/autonomous_fund agent."""

import pytest
from aea_test_autonomy.fixture_helpers import (  # noqa: F401
    abci_host,
    abci_port,
    flask_tendermint,
    ipfs_daemon,
    ipfs_domain,
    tendermint_port,
)

from packages.valory.agents.decentralized_watchtower.tests.helpers.fixtures import (
    UseHardHatWatchtowerBaseTest,
    UseMockApiBaseTest,
)
from packages.valory.agents.decentralized_watchtower.tests.test_agents.base import \
    BaseTestDecentralizedWatchtowerEnd2End
from packages.valory.skills.cow_orders_abci.rounds import SelectOrdersRound, RandomnessRound, SelectKeeperRound, \
    PlaceOrdersRound, VerifyExecutionRound
from packages.valory.skills.registration_abci.rounds import RegistrationStartupRound

TIME_TO_FINISH = 60  # 1 minute
TARGET_AGENT = "valory/decentralized_watchtower:0.1.0"
TARGET_SKILL = "valory/decentralized_watchtower_abci:0.1.0"


REGISTRATION_CHECK_STRINGS = (
    f"Entered in the '{RegistrationStartupRound.auto_round_id()}' round for period 0",
    f"'{RegistrationStartupRound.auto_round_id()}' round is done",
)
ORDER_CHECK_STRINGS = (
    f"Entered in the '{SelectOrdersRound.auto_round_id()}' round for period 0",
    f"'{SelectOrdersRound.auto_round_id()}' round is done",
    f"Entered in the '{RandomnessRound.auto_round_id()}' round for period 0",
    f"'{RandomnessRound.auto_round_id()}' round is done",
    f"Entered in the '{SelectKeeperRound.auto_round_id()}' round for period 0",
    f"'{SelectKeeperRound.auto_round_id()}' round is done",
    f"Entered in the '{PlaceOrdersRound.auto_round_id()}' round for period 0",
    f"'{PlaceOrdersRound.auto_round_id()}' round is done",
    f"Entered in the '{VerifyExecutionRound.auto_round_id()}' round for period 0",
)


@pytest.mark.parametrize("nb_nodes", (1,))
class TestAutonomousFundSingleAgent(
    BaseTestDecentralizedWatchtowerEnd2End,
    UseMockApiBaseTest,
    UseHardHatWatchtowerBaseTest,
):
    """
    Test the Decentralized Watchtower through the happy path, when using a single agent.

    By running this test, we spawn up a single agent service, along with the external dependencies:
        - tendermint
        - a test network
        - a mock order API server
    The test firstly takes care of the setting up the dependencies, and then runs the service.
    The test passes if the agent produces all the logs in specified in `strict_check_strings`.
    """

    agent_package = TARGET_AGENT
    skill_package = TARGET_SKILL
    wait_to_finish = TIME_TO_FINISH
    strict_check_strings = (
        REGISTRATION_CHECK_STRINGS
        + ORDER_CHECK_STRINGS
    )
    use_benchmarks = True


@pytest.mark.parametrize("nb_nodes", (2,))
class TestAutonomousFundTwoAgents(
    BaseTestDecentralizedWatchtowerEnd2End,
    UseMockApiBaseTest,
    UseHardHatWatchtowerBaseTest,
):
    """
    Test the Decentralized Watchtower through the "happy path", when using two agents.

    By running this test, we spawn up a single agent service, along with the external dependencies:
        - tendermint
        - a hardhat network
        - a mock Order API server
    The test firstly takes care of the setting up the dependencies, and then runs the service.
    The test passes if both agents produce all the logs in specified in `strict_check_strings`.
    """

    agent_package = TARGET_AGENT
    skill_package = TARGET_SKILL
    wait_to_finish = TIME_TO_FINISH
    strict_check_strings = (
        REGISTRATION_CHECK_STRINGS
        + ORDER_CHECK_STRINGS
    )
    use_benchmarks = True


@pytest.mark.parametrize("nb_nodes", (4,))
class TestAutonomousFundFourAgents(
    BaseTestDecentralizedWatchtowerEnd2End,
    UseMockApiBaseTest,
    UseHardHatWatchtowerBaseTest,
):
    """
    Test the Decentralized Watchtower through the "happy path", when using 4 agents.

    By running this test, we spawn up a single agent service, along with the external dependencies:
        - tendermint
        - a hardhat network
        - a mock Order API server
    The test firstly takes care of the setting up the dependencies, and then runs the service.
    The test passes if all 4 agents produce all the logs in specified in `strict_check_strings`.
    """

    agent_package = TARGET_AGENT
    skill_package = TARGET_SKILL
    wait_to_finish = TIME_TO_FINISH
    strict_check_strings = (
        REGISTRATION_CHECK_STRINGS
        + ORDER_CHECK_STRINGS
    )
    use_benchmarks = True
