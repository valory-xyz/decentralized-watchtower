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
"""This module contains an implementation of py_eth_utils utils."""

try:
    from Crypto.Hash import keccak

    def sha3_256(x: bytes) -> bytes:
        """Compute the SHA3-256 hash of the input bytes."""
        return keccak.new(digest_bits=256, data=x).digest()

except ImportError:
    import sha3 as _sha3

    def sha3_256(x: bytes) -> bytes:
        """Compute the SHA3-256 hash of the input bytes."""
        return _sha3.keccak_256(x).digest()


import random

import rlp
from eth_utils import big_endian_to_int, decode_hex
from eth_utils import encode_hex as encode_hex_0x
from eth_utils import int_to_big_endian
from py_ecc.secp256k1 import ecdsa_raw_recover, ecdsa_raw_sign, privtopub
from rlp.sedes import BigEndianInt, Binary, big_endian_int
from rlp.utils import ALL_BYTES


try:
    import coincurve
except ImportError:
    import warnings

    warnings.warn("could not import coincurve", ImportWarning)
    coincurve = None


class Memoize:
    def __init__(self, fn):
        self.fn = fn
        self.memo = {}

    def __call__(self, *args):
        if args not in self.memo:
            self.memo[args] = self.fn(*args)
        return self.memo[args]


TT256 = 2**256
TT256M1 = 2**256 - 1
TT255 = 2**255
SECP256K1P = 2**256 - 4294968273


def is_numeric(x: any) -> bool:
    """Check if a value is numeric."""
    return isinstance(x, int)


def is_string(x: any) -> bool:
    """Check if a value is a string."""
    return isinstance(x, bytes)


def to_string(value: any) -> bytes:
    """Convert a value to bytes."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return bytes(value, "utf-8")
    if isinstance(value, int):
        return bytes(str(value), "utf-8")


def int_to_bytes(value: int) -> bytes:
    """Convert an integer to bytes."""
    if isinstance(value, bytes):
        return value
    return int_to_big_endian(value)


def to_string_for_regexp(value: any) -> str:
    """Convert a value to a string suitable for regular expressions."""
    return str(to_string(value), "utf-8")


unicode = str


def bytearray_to_bytestr(value: bytearray) -> bytes:
    """Convert a bytearray to bytes."""
    return bytes(value)


def encode_int32(v: int) -> bytes:
    """Encode an integer as a 32-byte big-endian value."""
    return v.to_bytes(32, byteorder="big")


def bytes_to_int(value: bytes) -> int:
    """Convert bytes to an integer."""
    return int.from_bytes(value, byteorder="big")


def str_to_bytes(value: any) -> bytes:
    """Convert a value to bytes."""
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes):
        return value
    return bytes(value, "utf-8")


def ascii_chr(n: int) -> bytes:
    """Convert an ASCII code to a byte."""
    return ALL_BYTES[n]


def encode_hex(n: any) -> str:
    """Encode a value as a hexadecimal string."""
    if isinstance(n, str):
        return encode_hex(n.encode("ascii"))
    return encode_hex_0x(n)[2:]


def ecrecover_to_pub(rawhash: bytes, v: int, r: int, s: int) -> bytes:
    """Recover the public key from an ECDSA signature."""
    if coincurve and hasattr(coincurve, "PublicKey"):
        try:
            pk = coincurve.PublicKey.from_signature_and_message(
                zpad(bytearray_to_bytestr(int_to_32bytearray(r)), 32)
                + zpad(bytearray_to_bytestr(int_to_32bytearray(s)), 32)
                + ascii_chr(v - 27),
                rawhash,
                hasher=None,
            )
            pub = pk.format(compressed=False)[1:]
        except BaseException:
            pub = b"\x00" * 64
    else:
        result = ecdsa_raw_recover(rawhash, (v, r, s))
        if result:
            x, y = result
            pub = encode_int32(x) + encode_int32(y)
        else:
            raise ValueError("Invalid VRS")
    assert len(pub) == 64
    return pub


def ecsign(rawhash: bytes, key: bytes) -> tuple:
    """Create an ECDSA signature for the given hash and private key."""
    if coincurve and hasattr(coincurve, "PrivateKey"):
        pk = coincurve.PrivateKey(key)
        signature = pk.sign_recoverable(rawhash, hasher=None)
        v = safe_ord(signature[64]) + 27
        r = big_endian_to_int(signature[0:32])
        s = big_endian_to_int(signature[32:64])
    else:
        v, r, s = ecdsa_raw_sign(rawhash, key)
    return v, r, s


def mk_contract_address(sender: bytes, nonce: int) -> bytes:
    """Create a contract address using sender's address and nonce."""
    return sha3(rlp.encode([normalize_address(sender), nonce]))[12:]


def mk_metropolis_contract_address(sender: bytes, initcode: bytes) -> bytes:
    """Create a contract address using sender's address and initcode."""
    return sha3(normalize_address(sender) + initcode)[12:]


def safe_ord(value: any) -> int:
    """Safely convert a value to its ASCII code."""
    if isinstance(value, int):
        return value
    else:
        return ord(value)


# decorator


def debug(label: str) -> callable:
    """Decorator to facilitate debugging function calls."""

    def deb(f: callable) -> callable:
        def inner(*args, **kwargs) -> any:
            i = random.randrange(1000000)
            print(label, i, "start", args)
            x = f(*args, **kwargs)
            print(label, i, "end", x)
            return x

        return inner

    return deb


def flatten(li: list) -> list:
    """Flatten a list of lists."""
    o = []
    for l in li:
        o.extend(l)
    return o


def bytearray_to_int(arr: bytearray) -> int:
    """Convert a bytearray to an integer."""
    o = 0
    for a in arr:
        o = (o << 8) + a
    return o


def int_to_32bytearray(i: int) -> bytearray:
    """Convert an integer to a 32-byte bytearray."""
    o = [0] * 32
    for x in range(32):
        o[31 - x] = i & 0xFF
        i >>= 8
    return o


# sha3_count = [0]


def sha3(seed: bytes) -> bytes:
    """Compute the SHA3 hash of the input bytes."""
    return sha3_256(to_string(seed))


assert (
    encode_hex(sha3(b""))
    == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
)


@Memoize
def privtoaddr(k: bytes) -> bytes:
    """Compute the Ethereum address from a private key."""
    k = normalize_key(k)
    x, y = privtopub(k)
    return sha3(encode_int32(x) + encode_int32(y))[12:]


def checksum_encode(addr: bytes) -> str:
    """Checksum encode an Ethereum address."""
    addr = normalize_address(addr)
    o = ""
    v = big_endian_to_int(sha3(encode_hex(addr)))
    for i, c in enumerate(encode_hex(addr)):
        if c in "0123456789":
            o += c
        else:
            o += c.upper() if (v & (2 ** (255 - 4 * i))) else c.lower()
    return "0x" + o


def check_checksum(addr: str) -> bool:
    """Check if an Ethereum address has a valid checksum."""
    return checksum_encode(normalize_address(addr)) == addr


def normalize_address(x: any, allow_blank: bool = False) -> bytes:
    """Normalize an Ethereum address."""
    if is_numeric(x):
        return int_to_addr(x)
    if allow_blank and x in {"", b""}:
        return b""
    if len(x) in (42, 50) and x[:2] in {"0x", b"0x"}:
        x = x[2:]
    if len(x) in (40, 48):
        x = decode_hex(x)
    if len(x) == 24:
        assert len(x) == 24 and sha3(x[:20])[:4] == x[-4:]
        x = x[:20]
    if len(x) != 20:
        raise Exception("Invalid address format: %r" % x)
    return x


def normalize_key(key: any) -> bytes:
    """Normalize an Ethereum private key."""
    if is_numeric(key):
        o = encode_int32(key)
    elif len(key) == 32:
        o = key
    elif len(key) == 64:
        o = decode_hex(key)
    elif len(key) == 66 and key[:2] == "0x":
        o = decode_hex(key[2:])
    else:
        raise Exception("Invalid key format: %r" % key)
    if o == b"\x00" * 32:
        raise Exception("Zero privkey invalid")
    return o


def int_to_addr(x):
    """Convert an integer to an address."""
    o = [b""] * 20
    for i in range(20):
        o[19 - i] = ascii_chr(x & 0xFF)
        x >>= 8
    return b"".join(o)


def zpad(x: bytes, l: int) -> bytes:
    """Left zero pad value `x` to length `l`."""
    return b"\x00" * max(0, l - len(x)) + x


def rzpad(value: bytes, total_length: int) -> bytes:
    """Right zero pad value `x` to length `l`."""
    return value + b"\x00" * max(0, total_length - len(value))


def int_to_hex(x: int) -> str:
    """Convert an integer to a hexadecimal string."""
    o = encode_hex(encode_int(x))
    return "0x" + (o[1:] if (len(o) > 0 and o[0] == b"0") else o)


def remove_0x_head(s: str) -> str:
    """Remove the '0x' prefix from a string."""
    return s[2:] if s[:2] in (b"0x", "0x") else s


def parse_as_bin(s: str) -> bytes:
    """Parse a string as bytes."""
    return decode_hex(s[2:] if s[:2] == "0x" else s)


def parse_as_int(s: str) -> int:
    """Parse a string as an integer."""
    return s if is_numeric(s) else int("0" + s[2:], 16) if s[:2] == "0x" else int(s)


def print_func_call(
    ignore_first_arg: bool = False, max_call_number: int = 100
) -> callable:
    """Decorator to facilitate debugging by printing function calls."""
    from functools import wraps

    def display(x: any) -> str:
        x = to_string(x)
        try:
            x.decode("ascii")
        except BaseException:
            return "NON_PRINTABLE"
        return x

    local = {"call_number": 0}

    def inner(f: callable) -> callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> any:
            local["call_number"] += 1
            tmp_args = args[1:] if ignore_first_arg and len(args) else args
            this_call_number = local["call_number"]
            print(
                (
                    "{0}#{1} args: {2}, {3}".format(
                        f.__name__,
                        this_call_number,
                        ", ".join([display(x) for x in tmp_args]),
                        ", ".join(
                            display(key) + "=" + to_string(value)
                            for key, value in kwargs.items()
                        ),
                    )
                )
            )
            res = f(*args, **kwargs)
            print(
                (
                    "{0}#{1} return: {2}".format(
                        f.__name__, this_call_number, display(res)
                    )
                )
            )

            if local["call_number"] > 100:
                raise Exception("Reached max call number!")
            return res

        return wrapper

    return inner


def dump_state(trie: any) -> str:
    """Dump the contents of a Merkle Trie."""
    res = ""
    for k, v in list(trie.to_dict().items()):
        res += "%r:%r\n" % (encode_hex(k), encode_hex(v))
    return res


class Denoms:
    def __init__(self):
        self.wei = 1
        self.babbage = 10**3
        self.ada = 10**3
        self.kwei = 10**6
        self.lovelace = 10**6
        self.mwei = 10**6
        self.shannon = 10**9
        self.gwei = 10**9
        self.szabo = 10**12
        self.finney = 10**15
        self.mether = 10**15
        self.ether = 10**18
        self.turing = 2**256 - 1


denoms = Denoms()


address = Binary.fixed_length(20, allow_empty=True)
int20 = BigEndianInt(20)
int32 = BigEndianInt(32)
int256 = BigEndianInt(256)
hash32 = Binary.fixed_length(32)
trie_root = Binary.fixed_length(32, allow_empty=True)
