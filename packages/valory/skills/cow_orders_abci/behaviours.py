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
import json
from abc import ABC
from collections import deque
from copy import deepcopy
from typing import Any, Deque, Dict, Generator, List, Set, Type, cast

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.abstract_round_abci.common import (
    RandomnessBehaviour as BaseRandomnessBehaviour,
)
from packages.valory.skills.abstract_round_abci.common import (
    SelectKeeperBehaviour as BaseSelectKeeperBehaviour,
)
from packages.valory.skills.cow_orders_abci.models import Params
from packages.valory.skills.cow_orders_abci.rounds import (
    CowOrdersAbciApp,
    PlaceOrdersPayload,
    PlaceOrdersRound,
    RandomnessPayload,
    RandomnessRound,
    SelectKeeperPayload,
    SelectKeeperRound,
    SelectOrdersPayload,
    SelectOrdersRound,
    SynchronizedData,
    VerifyExecutionPayload,
    VerifyExecutionRound,
)


ORDERS = "ready_orders"
DEFAULT_HTTP_HEADERS = {
    "Content-Type": "application/json",
    "accept": "application/json",
}


class CowOrdersBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the cow_orders_abci skill."""

    @property
    def orders(self) -> List[Dict[str, Any]]:
        """
        Return the orders from shared state.

        Use with care, the returned data here is NOT synchronized with the rest of the agents.

        :return: the orders
        """
        orders = deepcopy(self.context.shared_state.get(ORDERS, []))
        return cast(List[Dict[str, Any]], orders)

    def remove_order(self, order: Dict[str, Any]) -> None:
        """
        Pop the order from shared state.

        :param order: the order
        """
        orders = self.orders
        orders.remove(order)
        self.context.shared_state[ORDERS] = orders

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    @staticmethod
    def serialized_keepers(keepers: Deque[str], keeper_retries: int) -> str:
        """Get the keepers serialized."""
        if len(keepers) == 0:
            return ""
        keepers_ = "".join(keepers)
        keeper_retries_ = keeper_retries.to_bytes(32, "big").hex()
        concatenated = keeper_retries_ + keepers_

        return concatenated


class PlaceOrdersBehaviour(CowOrdersBaseBehaviour):
    """PlaceOrdersBehaviour"""

    matching_round: Type[AbstractRound] = PlaceOrdersRound

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - If the agent is the keeper, then prepare the transaction and send it.
        - Otherwise, wait until the next round.
        - If a timeout is hit, set exit A event, otherwise set done event.
        """
        if self._i_am_not_sending():
            yield from self._not_sender_act()
        else:
            yield from self._sender_act()

    def _i_am_not_sending(self) -> bool:
        """Indicates if the current agent is the sender or not."""
        return (
            self.context.agent_address
            != self.synchronized_data.most_voted_keeper_address
        )

    def _not_sender_act(self) -> Generator:
        """Do the non-sender action."""
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            self.context.logger.info(
                f"Waiting for the keeper to do its keeping: {self.synchronized_data.most_voted_keeper_address}"
            )
            yield from self.wait_until_round_end()
        self.set_done()

    def _sender_act(self) -> Generator:
        """Do the sender action."""
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            order = self.synchronized_data.order
            order_uid = yield from self._place_order(order)
            self.context.logger.info(f"Order {order} placed with uid {order_uid}")
            sender = self.context.agent_address
            payload = PlaceOrdersPayload(sender=sender, content=order_uid)
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()
        self.set_done()

    def _place_order(self, order: Dict[str, Any]) -> Generator[None, None, str]:
        """Places the order on the CoW Api, and return the order uid."""
        order_bytes = json.dumps(order).encode()
        response = yield from self.get_http_response(
            method="POST",
            url=self.params.cow_api_url + "/orders",
            headers=DEFAULT_HTTP_HEADERS,
            content=order_bytes,
        )
        if response.status_code != 201:
            self.context.logger.error(
                f"Could not retrieve submit order to CoW API. "
                f"Received status code {response.status_code} response body: {response.body.decode()}."
            )
            return PlaceOrdersRound.ERROR_PAYLOAD

        order_uid = response.body.decode()
        return order_uid


class RandomnessBehaviour(BaseRandomnessBehaviour, CowOrdersBaseBehaviour):
    """RandomnessBehaviour"""

    matching_round: Type[AbstractRound] = RandomnessRound
    payload_class = RandomnessPayload


class SelectKeeperBehaviour(BaseSelectKeeperBehaviour, CowOrdersBaseBehaviour):
    """SelectKeeperBehaviour"""

    matching_round: Type[AbstractRound] = SelectKeeperRound
    payload_class = SelectKeeperPayload

    def async_act(self) -> Generator:
        """Do the action."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            keepers = deque((self._select_keeper(),))
            payload = self.payload_class(
                self.context.agent_address, self.serialized_keepers(keepers, 1)
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class SelectOrdersBehaviour(CowOrdersBaseBehaviour):
    """SelectOrdersBehaviour"""

    matching_round: Type[AbstractRound] = SelectOrdersRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            content = self.get_payload_content()
            payload = SelectOrdersPayload(sender=sender, content=content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_payload_content(self) -> str:
        """Get the payload content."""
        # remove the orders we have already processed
        self._handle_processed_orders()

        # check if there are any orders left to process
        if len(self.orders) == 0:
            return SelectOrdersRound.NO_ORDERS_PAYLOAD

        # select an order to be processed
        order = self.orders.pop()
        order_str = json.dumps(order, sort_keys=True)
        return order_str

    def _handle_processed_orders(self) -> None:
        """Handle orders that have been processed before."""
        prev_verified_order = self.synchronized_data.verified_order
        if prev_verified_order is None:
            return
        self.context.logger.info(
            f"Order {prev_verified_order} has already been verified. "
            f"Removing it from the list of orders to be processed."
        )
        self.remove_order(prev_verified_order)


class VerifyExecutionBehaviour(CowOrdersBaseBehaviour):
    """VerifyExecutionBehaviour"""

    matching_round: Type[AbstractRound] = VerifyExecutionRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            content = yield from self.get_payload_content()
            payload = VerifyExecutionPayload(sender=sender, content=content)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_payload_content(self) -> Generator[None, None, str]:
        """Get the payload content based on verification outcome."""
        order_uid = self.synchronized_data.order_uid
        order = self.synchronized_data.order
        verification_outcome = yield from self._verify_submission(order_uid, order)
        if verification_outcome == VerifyExecutionRound.VERIFICATION_OK:
            return VerifyExecutionRound.VERIFICATION_OK

        # something went wrong, the order was not submitted correctly
        return VerifyExecutionRound.VERIFICATION_FAILED

    def _verify_submission(
        self, reported_order_uid: str, order: Dict[str, Any]
    ) -> Generator[None, None, bool]:
        """
        Verify that the order was submitted.

        :param reported_order_uid: the order uid reported by the keeper
        :param order: the order to verify
        :returns: the appropriate payload content depending on the verification result
        """
        expected_order_uid = f'"{order["order_uid"]}"'
        if (
            reported_order_uid != PlaceOrdersRound.ERROR_PAYLOAD
            and reported_order_uid != expected_order_uid
        ):
            self.context.logger.warning(
                f"Order {order} was not submitted correctly. "
                f"Expected uid {expected_order_uid}, got {reported_order_uid}"
            )
            return VerifyExecutionRound.VERIFICATION_FAILED

        was_submitted = yield from self._was_order_submitted(order["order_uid"])
        if not was_submitted:
            self.context.logger.warning(f"Order {order} was not submitted.")
            return VerifyExecutionRound.VERIFICATION_FAILED

        return VerifyExecutionRound.VERIFICATION_OK

    def _was_order_submitted(self, order_uid: str) -> Generator[None, None, bool]:
        """Check that the order was submitted to the api."""
        url = self.params.cow_api_url + "/orders/" + order_uid
        response = yield from self.get_http_response(
            method="GET",
            url=url,
            headers=DEFAULT_HTTP_HEADERS,
        )
        if response.status_code != 200:
            self.context.logger.error(
                f"Could not get order with uid {order_uid}. "
                f"Received status code {response.status_code} response body: {response.body.decode()}."
            )
            return False

        # if the response is 200, the order was submitted
        return True


class CowOrdersRoundBehaviour(AbstractRoundBehaviour):
    """CowOrdersRoundBehaviour"""

    initial_behaviour_cls = SelectOrdersBehaviour
    abci_app_cls = CowOrdersAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        PlaceOrdersBehaviour,
        RandomnessBehaviour,
        SelectKeeperBehaviour,
        SelectOrdersBehaviour,
        VerifyExecutionBehaviour,
    ]
