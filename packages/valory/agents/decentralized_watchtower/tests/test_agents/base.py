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
# pylint: disable=broad-except,unspecified-encoding,import-error,redefined-outer-name

"""End2End tests base classes for the Autonomous Fund."""
from pathlib import Path

from aea_test_autonomy.base_test_classes.agents import BaseTestEnd2End

TERMINATION_TIMEOUT = 120


class BaseTestDecentralizedWatchtowerEnd2End(
    BaseTestEnd2End
):  # pylint: disable=too-few-public-methods
    """
    Extended base class for conducting E2E tests with the Decentralized Watchtower.

    Test subclasses must set NB_AGENTS, agent_package, wait_to_finish and check_strings.
    """

    cli_log_options = ["-v", "INFO"]  # no need for debug
    skill_package = "valory/decentralized_watchtower_abci:0.1.0"
    package_registry_src_rel = Path(__file__).parents[5]

    def test_run(self, nb_nodes: int) -> None:
        """Run the test."""
        self.prepare_and_launch(nb_nodes)
        self.health_check(
            max_retries=self.HEALTH_CHECK_MAX_RETRIES,
            sleep_interval=self.HEALTH_CHECK_SLEEP_INTERVAL,
        )
        self.check_aea_messages()
        self.terminate_agents(timeout=TERMINATION_TIMEOUT)
