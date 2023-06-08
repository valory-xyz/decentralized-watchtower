# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023Valory AG
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

"""This module contains the class to connect to an Gnosis Safe contract."""
import logging
from typing import Any, Optional

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi

PUBLIC_ID = PublicId.from_str("valory/composable_cow:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


class ComposableCowContract(Contract):
    """The ComposableCow contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def get_raw_transaction(
            cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> Optional[JSONLike]:
        """Get the Safe transaction."""
        raise NotImplementedError

    @classmethod
    def get_raw_message(
            cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> Optional[bytes]:
        """Get raw message."""
        raise NotImplementedError

    @classmethod
    def get_state(
            cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> Optional[JSONLike]:
        """Get state."""
        raise NotImplementedError

    @classmethod
    def get_tradeable_order(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            owner_address: str,
            sender_address: str,
            static_input: bytes,
            offchain_input: bytes,
    ) -> Optional[JSONLike]:
        """Get tradeable order."""
        instance = cls.get_instance(ledger_api, contract_address)
        order_data = instance.functions.getTradeableOrder(owner_address, sender_address, static_input,
                                                          offchain_input).call()
        return dict(data=order_data)

    @classmethod
    def process_order_events(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        tx_hash: str
    ) -> JSONLike:
        """Process order events"""
        contract = cls.get_instance(ledger_api, contract_address)
        receipt = ledger_api.api.eth.getTransactionReceipt(tx_hash)
        conditional_orders = contract.events.ConditionalOrderCreated().processReceipt(receipt)
        merkle_root_set = contract.events.MerkleRootSet().processReceipt(receipt)
        return dict(conditional_orders=conditional_orders, merkle_root_set=merkle_root_set)
