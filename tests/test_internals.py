from synergy_file_reader._synergy_file_reader import ValueError_to_FormatMismatch, FormatMismatch
from pytest import raises

def test_ValueError_to_FormatMismatch():
	with raises(FormatMismatch):
		with ValueError_to_FormatMismatch():
			raise ValueError
