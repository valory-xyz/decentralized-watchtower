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
# pylint: disable=line-too-long,too-many-ancestors,unused-argument
"""This package contains round behaviours of CowOrdersAbciApp."""
from typing import Set, Type

from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.cow_orders_abci.behaviours import CowOrdersRoundBehaviour
from packages.valory.skills.decentralized_watchtower_abci.composition import DecentralizedWatchtowerAbciApp
from packages.valory.skills.registration_abci.behaviours import RegistrationStartupBehaviour, \
    AgentRegistrationRoundBehaviour
from packages.valory.skills.reset_pause_abci.behaviours import ResetPauseABCIConsensusBehaviour


class CowOrdersRoundBehaviours(AbstractRoundBehaviour):
    """CowOrdersRoundBehaviours"""

    initial_behaviour_cls = RegistrationStartupBehaviour
    abci_app_cls = DecentralizedWatchtowerAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = {
        *AgentRegistrationRoundBehaviour.behaviours,
        *CowOrdersRoundBehaviour.behaviours,
        *ResetPauseABCIConsensusBehaviour.behaviours,
    }
