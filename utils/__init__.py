"""The utils package which contains database, finder, logger, players, and text
"""

import pymongo

from .database import Database
from .finder import Finder
from .logger import Logger
from .players import Players
from .server import Server
from .text import Text


class utils:
    """A class to hold all the utils classes"""

    def __init__(
        self,
        col: pymongo.collection.Collection,
        logger: Logger = None,
        debug=True,
    ):
        """Initializes the utils class

        Args:
            logger (Logger): The logger class
            col (pymongo.collection.Collection): The database collection
        """
        self.col = col
        self.logger = logger if logger else Logger(debug)
        self.logger.clear()
        self.text = Text(self.logger)
        self.server = Server(self.logger)
        self.database = Database()

        self.players = Players(
            logger=self.logger, col=self.col, server=self.server)
        self.finder = Finder(
            logger=self.logger, col=self.col, Text=self.text, Player=self.players
        )
