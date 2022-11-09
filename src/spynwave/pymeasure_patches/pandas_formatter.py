import logging
import re
import pandas as pd
from pymeasure.units import ureg

class Results_Formatter(logging.Formatter):
    """Base class for formatters."""
    def __init__(self, columns, delimiter=',', line_break='\n'):
        """Prepares formatter for a given list of columns (=header).
        :param columns: list of column names.
        :type columns: list
        :param delimiter: delimiter between columns, defaults to ','
        :type delimiter: str
        :param line_break: line termination character to use,
                           defaults to '\n'
        :type delimiter: str
        """
        super().__init__()
        self.columns = columns
        self.units = self._parse_columns(columns)
        self.delimiter = delimiter
        self.line_break = line_break

    @staticmethod
    def _parse_columns(columns):
        """Parse the columns to get units in parenthesis."""
        units_pattern = r"\((?P<units>[\w/\(\)\*\t]+)\)"
        units = {}
        for column in columns:
            match = re.search(units_pattern, column)
            if match:
                units[column] = ureg.Quantity(match.groupdict()['units']).units
        return units

class CSVFormatterPandas(Results_Formatter):
    """ Formatter of data results, pandas dataframe or single-line CSV """

    def format(self, record):
        """Formats a record as csv using pandas built-in ``to_csv`` method.
        Accepts a pandas dataframe or a dict of values matching
        the given list of columns.
        :param record: record to format.
        :type record: pandas.DataFrame or dict
        :return: str
        """
        if isinstance(record, pd.DataFrame):
            record = record.reindex(columns=self.columns)
        elif isinstance(record, dict):
            record = pd.DataFrame([record], columns=self.columns)
        else:
            raise TypeError('Formatting of data failed. '
                            'Pandas dataframe or dict required.')
        return record.to_csv(
            sep=self.delimiter,
            header=False,
            index=False,
            # explicit line_terminator required, otherwise Windows
            # uses \r\n which results in double blank lines
            lineterminator=self.line_break,
        ).strip()

    def format_header(self):
        record = pd.DataFrame(columns=self.columns)
        return record.to_csv(
            sep=self.delimiter,
            header=True,
            index=False,
            lineterminator=self.line_break,
        ).strip()