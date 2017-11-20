import logging
import datetime
import beancount.loader as loader
from beancount.core import prices
from beancount.core import realization
from beancount.core.data import Transaction, Posting, Amount, Close
from beancount.parser.printer import format_entry


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
        self.price_map = prices.build_price_map(entries)
        self.accounts = realization.realize(self.entries)

    def latest_price(self, item):
        for commodity, base in self.price_map.forward_pairs:
            if commodity == item:
                _, number = self.price_map[(commodity, base)][-1]
                return Amount(number, base)
        return None

    def add_posting(self, user, item):
        assert(user in self.get_users())
        assert(item in self.get_items().keys())
        account = "Assets:Receivable:{}".format(user)
        if self.transaction is None:
            self.transaction = Transaction(
                flag="*",
                payee="kitty",
                narration="cococount purchase",
                tags=None,
                postings=[Posting("Assets:Items", None, None, None, None, None)],
                links=None,
                meta=None,
                date=datetime.date.today())
        amount = self.latest_price(item)
        assert(amount is not None)
        self.transaction.postings.append(Posting(account, amount, None, None, None, None))
        self.log.debug(format_entry(self.transaction))

    def get_users(self):
        users = []
        for user, account in self.accounts["Assets"]["Receivable"].items():
            last_posting = realization.find_last_active_posting(account.txn_postings)
            if not isinstance(last_posting, Close):
                users.append(user)
        return users

    def get_items(self):
        items = {}
        for base, quote in self.price_map.forward_pairs:
            price_list = self.price_map[(base, quote)]
            _, number = price_list[-1]
            items[base] = float(number)
        return items

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
