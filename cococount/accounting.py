import logging
import datetime
import beancount.loader as loader
from beancount.core import prices
from beancount.core import realization
from beancount.core import convert
from beancount.core import number
from beancount.core.data import Transaction, Posting, Amount, Close
from beancount.parser.printer import format_entry
from beancount.parser import booking
from beancount.parser import options


class BeancountInterface:

    def __init__(self, filename):
        self.log = logging.getLogger("BeancountInterface")
        self.filename = filename
        self.transaction = None
        self.reload()

    def reload(self):
        if self.transaction is not None:
            self.log.warn("Discard transactions due to reload")
            self.log.warn(format_entry(self.transaction))
        entries, errors, options_map = loader.load_file(self.filename)
        assert(len(errors) == 0)
        self.entries = entries
        self.options_map = options_map
        self.transaction = None
        # Commonly used transformations of the entries
        self.price_entries = prices.get_last_price_entries(entries, datetime.date.today())
        self.accounts = realization.realize(self.entries)

    def latest_price(self, item_id):
        prices = [p for p in self.price_entries if p.currency == item_id]
        assert(len(prices) == 1)
        return prices[0]

    def add_posting(self, user, item_id):
        assert(user in self.get_users())
        account = "Assets:Receivable:{}".format(user)
        if self.transaction is None:
            self.transaction = Transaction(
                flag="*",
                payee="kitty",
                narration="cococount purchase",
                tags=None,
                postings=[Posting("Assets:Items", number.MISSING, None, None, None, {})],
                links=None,
                meta={},
                date=datetime.date.today())
        price = self.latest_price(item_id)
        self.transaction.postings.append(
                Posting(account, price.amount, None, None, None, {}))
        self.log.debug(format_entry(self.transaction))

    def get_users(self):
        users = []
        for user, account in self.accounts["Assets"]["Receivable"].items():
            last_posting = realization.find_last_active_posting(account.txn_postings)
            if not isinstance(last_posting, Close):
                users.append(user)
        return users

    def get_items(self):
        items = []
        for price in self.price_entries:
            name = price.meta["display-as"] if "display-as" in price.meta else price.currency
            items.append({
                    "item-id" : price.currency,
                    "display-as" : name,
                    "amount" : float(price.amount.number)})
        return sorted(items, key=lambda item : item["amount"])

    def get_balances(self):
        if self.transaction is None:
            accounts = self.accounts
        else:
            entries, balance_errors = booking.book(
                    self.entries + [self.transaction],
                    options.OPTIONS_DEFAULTS.copy())
            assert(len(balance_errors) == 0)
            accounts = realization.realize(entries)
        balances = {}
        for user, account in accounts["Assets"]["Receivable"].items():
            last_posting = realization.find_last_active_posting(account.txn_postings)
            if not isinstance(last_posting, Close):
                positions = account.balance.reduce(convert.get_cost).get_positions()
                amounts = [position.units for position in positions]
                assert(len(amounts) < 2)
                if len(amounts) == 1:
                    balances[user] = str(-amounts[0])
                else:
                    balances[user] = "0.00 EUR"
        return balances

    def flush(self):
        self.log.debug("flush transactions to file")
        if self.transaction is not None:
            self.log.debug(format_entry(self.transaction))
            with open(self.filename, "a") as handle:
                handle.write("\n")
                handle.write(format_entry(self.transaction))
        else:
            self.log.debug("no transactions to flush")
        self.transaction = None

    def close(self):
        self.flush()
