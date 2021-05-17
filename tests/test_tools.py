from synergy_file_reader.tools import (
		split_well_name, extract_channel,
		parse_time, parse_timestamp,
		row_iter,
		LineBuffer,
	)
from math import nan
import numpy as np
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

@mark.parametrize("string",["Max V [OD:600","abc"])
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
			( "?????"  ,   nan),
		]
	)
def test_parse_time(string,seconds):
	np.testing.assert_equal( parse_time(string), seconds )

@mark.parametrize(
		"string, number, seconds",
		[
			( "Time 1 (0:09:10)"   ,  1,   550 ),
			( "Time  98 (16:19:10)", 98, 58750 ),
		]
	)
def test_parse_timestamp(string,number,seconds):
	assert parse_timestamp(string) == (number,seconds)

@mark.parametrize("string",["Time 1 (0:09:10","abc"])
def test_parse_bad_timestamp(string):
	with raises(ValueError):
		parse_timestamp(string)

def test_row_iter():
	items = list(row_iter())
	assert items[0] == "A"
	assert items[25] == "Z"
	assert items[26] == "AA"
	assert items[28] == "AC"
	assert items[81] == "CD"

def test_LineBuffer():
	lb = LineBuffer(["","","a","b","","c","","","d","e","","","f",""])
	
	for line in lb:
		pass
	assert line==""
	
	for _ in range(3):
		for line,control in zip(lb,["a","b","","c","","","d"]):
			assert lb
			assert line==control
	
	with raises(ValueError):
		with lb as lb_iter:
			for line,control in zip(lb_iter,["a","b","","c"]):
				assert lb
				assert line==control
			raise ValueError
	
	with lb as lb_iter:
		for line,control in zip(lb_iter,["a","b","","c"]):
			assert lb
			assert line==control
	
	for line,control in zip(lb,["d","e","","","f"]):
		assert lb
		assert line==control
	lb.clear()
	
	assert not lb
	for line in lb:
		raise AssertionError


