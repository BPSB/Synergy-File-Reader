from synergy_file_reader.tools import split_well_name, to_seconds, LineBuffer, extract_channel
from pytest import mark, raises

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

@mark.parametrize("well",["A","1","OD:600"])
def test_split_bad_well(well):
	with raises(ValueError):
		split_well_name(well)

@mark.parametrize(
		"string, name, channel",
		[
			( "Max V [OD:600]" , "Max V"     , "OD:600" ),
			( "Lagtime [YFP]"  , "Lagtime"   , "YFP"    ),
			( "R-Squared [CFP]", "R-Squared" , "CFP"    ),
		]
	)
def test_extract_channel(string,name,channel):
	assert extract_channel(string) == (name,channel)

@mark.parametrize("string",["Max V [OD:600"])
def test_extract_bad_channel(string):
	with raises(ValueError):
		extract_channel(string)

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


