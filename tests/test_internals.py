from synergy_file_reader._synergy_file_reader import (
		ValueError_to_FormatMismatch,
		FormatMismatch,
		format_parsers,
		TryFormats,
	)
from pytest import raises, mark

def test_ValueError_to_FormatMismatch():
	with raises(FormatMismatch):
		with ValueError_to_FormatMismatch():
			raise ValueError

def test_TryFormats_fail():
	number_of_attempts = 0
	with raises(FormatMismatch):
		for attempt in TryFormats():
			number_of_attempts += 1
			with attempt as format_parser:
				raise ValueError
	assert number_of_attempts == len(format_parsers)

@mark.parametrize("successes",
	[
		( True , True , False ),
		( False, True , False ),
		( True , False, False ),
	])
def test_TryFormats_success(successes):
	number_of_attempts = 0
	for success,attempt in zip(successes,TryFormats()):
		number_of_attempts += 1
		with attempt as format_parser:
			if not success:
				raise ValueError
	assert number_of_attempts == successes.index(True)+1

