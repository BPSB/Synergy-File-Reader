from synergy_file_reader.tools import split_well_name, to_seconds, LineBuffer
from pytest import mark

@mark.parametrize(
		"well, row, col",
		[
			( "A1"   , "A"  , 1   ),
			( "B12"  , "B"  , 12  ),
			( "AA1"  , "AA" , 1   ),
			( "ZX137", "ZX" , 137 ),
		]
	)
def test_split_well_name(well,row,col):
	assert split_well_name(well) == (row,col)

@mark.parametrize(
		"string, seconds",
		[
			( "0:00:01",     1),
			( "0:01:00",    60),
			( "1:00:00",  3600),
			( "2:34:56",  9296),
		]
	)
def test_to_seconds(string,seconds):
	assert to_seconds(string) == seconds

def test_LineBuffer():
	lb = LineBuffer(["","","a","b","","c","","","d","e","","","f",""])
	
	for line in lb:
		pass
	assert line==""
	
	for _ in range(3):
		for line,control in zip(lb,["a","b","","c","","","d"]):
			assert lb
			assert line==control
	
	for line,control in zip(lb,["a","b","","c"]):
		assert lb
		assert line==control
	lb.clear()
	
	for line,control in zip(lb,["d","e","","","f"]):
		assert lb
		assert line==control
	lb.clear()
	
	assert not lb
	for line in lb:
		raise AssertionError


