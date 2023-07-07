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

"""This package contains the composition for decentralized watchtower."""

from packages.valory.skills.abstract_round_abci.abci_app_chain import AbciAppTransitionMapping, chain
from packages.valory.skills.cow_orders_abci.rounds import SelectOrdersRound, CowOrdersAbciApp, FinishedWithOrdersRound
from packages.valory.skills.registration_abci.rounds import (
    FinishedRegistrationRound, RegistrationStartupRound, AgentRegistrationAbciApp)
from packages.valory.skills.reset_pause_abci.rounds import FinishedResetAndPauseRound, FinishedResetAndPauseErrorRound, \
    ResetPauseAbciApp, ResetAndPauseRound
from packages.valory.skills.termination_abci.rounds import BackgroundRound, TerminationAbciApp
from packages.valory.skills.termination_abci.rounds import Event as TerminationEvent

abci_app_transition_mapping: AbciAppTransitionMapping = {
    FinishedRegistrationRound: SelectOrdersRound,
    FinishedResetAndPauseRound: SelectOrdersRound,
    FinishedResetAndPauseErrorRound: RegistrationStartupRound,
    FinishedWithOrdersRound: ResetAndPauseRound,
}

DecentralizedWatchtowerAbciApp = chain(
    (
        AgentRegistrationAbciApp,
        CowOrdersAbciApp,
        ResetPauseAbciApp,
    ),
    abci_app_transition_mapping,
).add_termination(
    background_round_cls=BackgroundRound,
    termination_event=TerminationEvent.TERMINATE,
    termination_abci_app=TerminationAbciApp,
)
