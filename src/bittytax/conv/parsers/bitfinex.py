# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import re
from decimal import Decimal

from ..dataparser import DataParser
from ..out_record import TransactionOutRecord

WALLET = "Bitfinex"

PRECISION = Decimal("0.00000000")


def parse_bitfinex_trades_v2(data_row, _parser, **_kwargs):
    parse_bitfinex_trades_v1(data_row, _parser, **_kwargs)


def parse_bitfinex_trades_v1(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DATE"], dayfirst=True)

    if row_dict["FEE CURRENCY"]:
        fee_quantity = abs(Decimal(row_dict["FEE"]).quantize(PRECISION))
    else:
        fee_quantity = None

    if Decimal(row_dict["AMOUNT"]) > 0:
        sell_quantity = Decimal(row_dict["PRICE"]) * Decimal(row_dict["AMOUNT"])

        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["AMOUNT"],
            buy_asset=row_dict["PAIR"].split("/")[0],
            sell_quantity=sell_quantity.quantize(PRECISION),
            sell_asset=row_dict["PAIR"].split("/")[1],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["FEE CURRENCY"],
            wallet=WALLET,
        )
    else:
        buy_quantity = Decimal(row_dict["PRICE"]) * abs(Decimal(row_dict["AMOUNT"]))

        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity.quantize(PRECISION),
            buy_asset=row_dict["PAIR"].split("/")[1],
            sell_quantity=abs(Decimal(row_dict["AMOUNT"])),
            sell_asset=row_dict["PAIR"].split("/")[0],
            fee_quantity=fee_quantity,
            fee_asset=row_dict["FEE CURRENCY"],
            wallet=WALLET,
        )


def parse_bitfinex_deposits_withdrawals(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DATE"], dayfirst=True)

    if row_dict["STATUS"] != "COMPLETED":
        return

    if Decimal(row_dict["AMOUNT"]) > 0:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["AMOUNT"],
            buy_asset=row_dict["CURRENCY"],
            fee_quantity=abs(Decimal(row_dict["FEES"])),
            fee_asset=row_dict["CURRENCY"],
            wallet=WALLET,
        )
    else:
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["AMOUNT"])),
            sell_asset=row_dict["CURRENCY"],
            fee_quantity=abs(Decimal(row_dict["FEES"])),
            fee_asset=row_dict["CURRENCY"],
            wallet=WALLET,
        )


def parse_bitfinex_ledger(data_row, _parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["DATE"], dayfirst=True)

    if _is_referral(row_dict["DESCRIPTION"]):
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_GIFT_RECEIVED,
            data_row.timestamp,
            buy_quantity=row_dict["AMOUNT"],
            buy_asset=row_dict["CURRENCY"],
            wallet=WALLET,
        )


def _is_referral(description):
    if re.match(
        r"^Earned fees from user (\d+) on wallet exchange$|^Affiliate Rebate.*$",
        description,
    ):
        return True
    return False


DataParser(
    DataParser.TYPE_EXCHANGE,
    "Bitfinex Trades",
    [
        "#",
        "PAIR",
        "AMOUNT",
        "PRICE",
        "FEE",
        "FEE PERC",
        "FEE CURRENCY",
        "DATE",
        "ORDER ID",
    ],
    worksheet_name="Bitfinex T",
    # Different handler name used to prevent data file consolidation
    row_handler=parse_bitfinex_trades_v2,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Bitfinex Trades",
    ["#", "PAIR", "AMOUNT", "PRICE", "FEE", "FEE CURRENCY", "DATE", "ORDER ID"],
    worksheet_name="Bitfinex T",
    row_handler=parse_bitfinex_trades_v1,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Bitfinex Deposits/Withdrawals",
    [
        "#",
        "DATE",
        "CURRENCY",
        "STATUS",
        "AMOUNT",
        "FEES",
        "DESCRIPTION",
        "TRANSACTION ID",
        "NOTE",
    ],
    worksheet_name="Bitfinex D,W",
    row_handler=parse_bitfinex_deposits_withdrawals,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Bitfinex Deposits/Withdrawals",
    [
        "#",
        "DATE",
        "CURRENCY",
        "STATUS",
        "AMOUNT",
        "FEES",
        "DESCRIPTION",
        "TRANSACTION ID",
    ],
    worksheet_name="Bitfinex D,W",
    row_handler=parse_bitfinex_deposits_withdrawals,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Bitfinex Ledger",
    ["#", "DESCRIPTION", "CURRENCY", "AMOUNT", "BALANCE", "DATE", "WALLET"],
    worksheet_name="Bitfinex L",
    row_handler=parse_bitfinex_ledger,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Bitfinex Ledger",
    ["DESCRIPTION", "CURRENCY", "AMOUNT", "BALANCE", "DATE", "WALLET"],
    worksheet_name="Bitfinex L",
    row_handler=parse_bitfinex_ledger,
)
