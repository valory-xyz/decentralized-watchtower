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

"""This module contains tests for order_utils."""
from datetime import datetime, timezone

import pytest

from packages.valory.skills.order_monitoring.order_utils import (
    balance_to_string,
    compute_order_uid,
    extract_order_uid_params,
    hash_domain,
    kind_to_string,
    timestamp,
)


DUMMY_ORDER = {
    "sellToken": "0x0000000000000000000000000000000000000001",
    "buyToken": "0x0000000000000000000000000000000000000002",
    "receiver": "0x0000000000000000000000000000000000000000",
    "sellAmount": 10,
    "buyAmount": 1,
    "validTo": 1686755136,
    "appData": "0x320530c667bc337342614750b6b7ab2430bdd290c9fff11cdfebd685072ab171",
    "feeAmount": 0,
    "kind": "0xf3b277728b3fee749481eb3e0b3b48980dbbab78658fc419025cb16eee346775",
    "partiallyFillable": False,
    "sellTokenBalance": "0x5a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc9",
    "buyTokenBalance": "0x5a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc9",
    "signingScheme": "eip1271",
    "signature": "0x5fd7e97d853572232c7c6f7d864b0e1f2c09fda728374d44a6f216d6d44ce5109bf69584d5a25ba2e97094ad7d83dc28a6572da797d6b3e7fc6663bd93efb789fc17e489000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000000000000000000000000000000002200000000000000000000000000000000000000000000000000000000000000180000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000006489d740320530c667bc337342614750b6b7ab2430bdd290c9fff11cdfebd685072ab1710000000000000000000000000000000000000000000000000000000000000000f3b277728b3fee749481eb3e0b3b48980dbbab78658fc419025cb16eee34677500000000000000000000000000000000000000000000000000000000000000005a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc95a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc90000000000000000000000000000000000000000000000000000000000000280000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000024000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000b306bf915c4d645ff596e518faf3f9669b970160ef3f2f1ee1cf423392f5976e3d5b29b3eab3a41dada7159bc6e62113509555a00000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000000000140000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000006489d6c9000000000000000000000000000000000000000000000000000000000000000a00000000000000000000000000000000000000000000000000000000000000780000000000000000000000000000000000000000000000000000000000000000320530c667bc337342614750b6b7ab2430bdd290c9fff11cdfebd685072ab1710000000000000000000000000000000000000000000000000000000000000000",
    "from": "0xcD84cF5E892E77d65c396c50DD77A534Ea20b896",
}
DUMMY_OWNER = "0xcD84cF5E892E77d65c396c50DD77A534Ea20b896"
DUMMY_DOMAIN = {
    "chainId": 31337,
    "name": "Gnosis Protocol",
    "verifyingContract": "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
    "version": "v2",
}
BAD_DOMAIN = {
    **DUMMY_DOMAIN,
    "badField": "badValue",
}


def test_compute_order_uid() -> None:
    """Test compute_order_id."""
    # expected order uid is computed using the cowprotocol TS library https://github.com/cowprotocol/contracts
    expected_order_uid = "0xab05afe58e3ce97603c8229fe6fbac517307992df46a5552d02e1b5f1864fdc4cd84cf5e892e77d65c396c50dd77a534ea20b8966489d740"
    assert (
        compute_order_uid(DUMMY_DOMAIN, DUMMY_ORDER, DUMMY_OWNER) == expected_order_uid
    )


def test_hash_domain() -> None:
    """Test hash_domain."""
    with pytest.raises(ValueError) as e:
        hash_domain(BAD_DOMAIN)
    assert str(e.value) == "invalid typed-data domain key: 'badField'"


def test_timestamp_with_datetime() -> None:
    """Test timestamp function with a datetime object."""
    dt = datetime(2023, 6, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert timestamp(dt) == 1686744000


def test_timestamp_with_integer() -> None:
    """Test timestamp function with an integer."""
    assert timestamp(1673731200) == 1673731200


def test_balance_to_string_with_erc20_balance() -> None:
    """Test balance_to_string function with erc20 balance."""
    assert (
        balance_to_string(
            "0x5a28e9363bb942b639270062aa6bb295f434bcdfc42c97267bf003f272060dc9"
        )
        == "erc20"
    )


def test_balance_to_string_with_external_balance() -> None:
    """Test balance_to_string function with external balance."""
    assert (
        balance_to_string(
            "0xabee3b73373acd583a130924aad6dc38cfdc44ba0555ba94ce2ff63980ea0632"
        )
        == "external"
    )


def test_balance_to_string_with_internal_balance() -> None:
    """Test balance_to_string function with internal balance."""
    assert (
        balance_to_string(
            "0x4ac99ace14ee0a5ef932dc609df0943ab7ac16b7583634612f8dc35a4289a6ce"
        )
        == "internal"
    )


def test_balance_to_string_with_unknown_balance_type() -> None:
    """Test balance_to_string function with unknown balance type."""
    with pytest.raises(ValueError) as e:
        balance_to_string("0x1234567890")
    assert str(e.value) == "Unknown balance type: 0x1234567890"


def test_kind_to_string_with_sell_kind() -> None:
    """Test kind_to_string function with sell kind."""
    assert (
        kind_to_string(
            "0xf3b277728b3fee749481eb3e0b3b48980dbbab78658fc419025cb16eee346775"
        )
        == "sell"
    )


def test_kind_to_string_with_buy_kind() -> None:
    """Test kind_to_string function with buy kind."""
    assert (
        kind_to_string(
            "0x6ed88e868af0a1983e3886d5f3e95a2fafbd6c3450bc229e27342283dc429ccc"
        )
        == "buy"
    )


def test_kind_to_string_with_unknown_kind() -> None:
    """Test kind_to_string function with unknown kind."""
    with pytest.raises(ValueError) as e:
        kind_to_string("0xabcdef123456")
    assert str(e.value) == "Unknown kind: 0xabcdef123456"


def test_extract_order_uid_params() -> None:
    """Test extract order uid params."""
    order_uid_str = "0xab05afe58e3ce97603c8229fe6fbac517307992df46a5552d02e1b5f1864fdc4cd84cf5e892e77d65c396c50dd77a534ea20b8966489d740"
    order_uid = bytes.fromhex(order_uid_str[2:])
    extract_params = extract_order_uid_params(order_uid)

    assert extract_params.owner == DUMMY_OWNER
    assert extract_params.valid_to == DUMMY_ORDER["validTo"]


def test_extract_order_uid_params_bad_uid() -> None:
    """Test extract order uid params with bad uid."""
    bad_order_uid = b"bad_order_uid"
    with pytest.raises(ValueError) as e:
        extract_order_uid_params(bad_order_uid)
    assert str(e.value) == "Invalid order UID length"
