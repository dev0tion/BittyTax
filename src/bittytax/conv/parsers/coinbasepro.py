# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

import sys
from decimal import Decimal

from colorama import Fore

from ...config import config
from ..dataparser import DataParser
from ..exceptions import DataRowError, MissingComponentError, UnexpectedTypeError
from ..out_record import TransactionOutRecord

WALLET = "Coinbase Pro"


def parse_coinbase_pro_account_v2(data_rows, parser, **_kwargs):
    trade_ids = {}
    for dr in data_rows:
        if dr.row_dict["trade id"] in trade_ids:
            trade_ids[dr.row_dict["trade id"]].append(dr)
        else:
            trade_ids[dr.row_dict["trade id"]] = [dr]

    for data_row in data_rows:
        if config.debug:
            sys.stderr.write(
                f"{Fore.YELLOW}conv: "
                f"row[{parser.in_header_row_num + data_row.line_num}] {data_row}\n"
            )

        if data_row.parsed:
            continue

        try:
            _parse_coinbase_pro_row(trade_ids, parser, data_row)
        except DataRowError as e:
            data_row.failure = e
        except (ValueError, ArithmeticError) as e:
            if config.debug:
                raise

            data_row.failure = e


def _parse_coinbase_pro_row(trade_ids, parser, data_row):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])
    data_row.parsed = True

    if row_dict["type"] == "withdrawal":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["amount"])),
            sell_asset=row_dict["amount/balance unit"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "deposit":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["amount"],
            buy_asset=row_dict["amount/balance unit"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "match":
        if Decimal(row_dict["amount"]) < 0:
            sell_quantity = abs(Decimal(row_dict["amount"]))
            sell_asset = row_dict["amount/balance unit"]

            buy_quantity, buy_asset = _get_trade(trade_ids[row_dict["trade id"]], "match")
        else:
            buy_quantity = row_dict["amount"]
            buy_asset = row_dict["amount/balance unit"]

            sell_quantity, sell_asset = _get_trade(trade_ids[row_dict["trade id"]], "match")

        if sell_quantity is None or buy_quantity is None:
            raise MissingComponentError(
                parser.in_header.index("trade id"), "trade id", row_dict["trade id"]
            )

        fee_quantity, fee_asset = _get_trade(trade_ids[row_dict["trade id"]], "fee")

        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=buy_quantity,
            buy_asset=buy_asset,
            sell_quantity=sell_quantity,
            sell_asset=sell_asset,
            fee_quantity=fee_quantity,
            fee_asset=fee_asset,
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def _get_trade(trade_id_rows, t_type):
    quantity = None
    asset = ""

    for data_row in trade_id_rows:
        if not data_row.parsed and t_type == data_row.row_dict["type"]:
            quantity = abs(Decimal(data_row.row_dict["amount"]))
            asset = data_row.row_dict["amount/balance unit"]
            data_row.timestamp = DataParser.parse_timestamp(data_row.row_dict["time"])
            data_row.parsed = True
            break

    return quantity, asset


def parse_coinbase_pro_account_v1(data_row, parser, **_kwargs):
    # This legacy version only uses the account report for deposits/withdrawals
    # everything else comes from the fills report
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["time"])

    if row_dict["type"] == "withdrawal":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_WITHDRAWAL,
            data_row.timestamp,
            sell_quantity=abs(Decimal(row_dict["amount"])),
            sell_asset=row_dict["amount/balance unit"],
            wallet=WALLET,
        )
    elif row_dict["type"] == "deposit":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_DEPOSIT,
            data_row.timestamp,
            buy_quantity=row_dict["amount"],
            buy_asset=row_dict["amount/balance unit"],
            wallet=WALLET,
        )
    elif row_dict["type"] in ("match", "fee"):
        # Skip trades
        return
    else:
        raise UnexpectedTypeError(parser.in_header.index("type"), "type", row_dict["type"])


def parse_coinbase_pro_fills_v2(data_row, parser, **kwargs):
    # Deprecated, you can now use just the account statement
    parse_coinbase_pro_fills_v1(data_row, parser, **kwargs)


def parse_coinbase_pro_fills_v1(data_row, parser, **_kwargs):
    row_dict = data_row.row_dict
    data_row.timestamp = DataParser.parse_timestamp(row_dict["created at"])

    if row_dict["side"] == "BUY":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=row_dict["size"],
            buy_asset=row_dict["size unit"],
            sell_quantity=abs(Decimal(row_dict["total"])) - Decimal(row_dict["fee"]),
            sell_asset=row_dict["price/fee/total unit"],
            fee_quantity=row_dict["fee"],
            fee_asset=row_dict["price/fee/total unit"],
            wallet=WALLET,
        )
    elif row_dict["side"] == "SELL":
        data_row.t_record = TransactionOutRecord(
            TransactionOutRecord.TYPE_TRADE,
            data_row.timestamp,
            buy_quantity=Decimal(row_dict["total"]) + Decimal(row_dict["fee"]),
            buy_asset=row_dict["price/fee/total unit"],
            sell_quantity=row_dict["size"],
            sell_asset=row_dict["size unit"],
            fee_quantity=row_dict["fee"],
            fee_asset=row_dict["price/fee/total unit"],
            wallet=WALLET,
        )
    else:
        raise UnexpectedTypeError(parser.in_header.index("side"), "side", row_dict["side"])


ACCOUNT = DataParser(
    DataParser.TYPE_EXCHANGE,
    "Coinbase Pro Account",
    [
        "portfolio",
        "type",
        "time",
        "amount",
        "balance",
        "amount/balance unit",
        "transfer id",
        "trade id",
        "order id",
    ],
    worksheet_name="Coinbase Pro",
    all_handler=parse_coinbase_pro_account_v2,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Coinbase Pro Fills",
    [
        "portfolio",
        "trade id",
        "product",
        "side",
        "created at",
        "size",
        "size unit",
        "price",
        "fee",
        "total",
        "price/fee/total unit",
    ],
    worksheet_name="Coinbase Pro T",
    deprecated=ACCOUNT,
    # Different handler name used to prevent data file consolidation
    row_handler=parse_coinbase_pro_fills_v2,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Coinbase Pro Fills",
    [
        "trade id",
        "product",
        "side",
        "created at",
        "size",
        "size unit",
        "price",
        "fee",
        "total",
        "price/fee/total unit",
    ],
    worksheet_name="Coinbase Pro T",
    row_handler=parse_coinbase_pro_fills_v1,
)

DataParser(
    DataParser.TYPE_EXCHANGE,
    "Coinbase Pro Account",
    [
        "type",
        "time",
        "amount",
        "balance",
        "amount/balance unit",
        "transfer id",
        "trade id",
        "order id",
    ],
    worksheet_name="Coinbase Pro",
    row_handler=parse_coinbase_pro_account_v1,
)
