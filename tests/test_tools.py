from synergy_file_reader.tools import (
		row_iter, VALID_ROWS,
		split_alpha_and_number,
		split_well_name,
		is_sample_label_string, is_sample_id,
		extract_channel,
		parse_time, parse_timestamp, parse_number,
		LineBuffer,
	)
from math import nan, isnan, inf
import numpy as np
from pytest import mark, raises

def test_row_iter():
	items = list(row_iter(exhaust_warning=False))
	assert set(items) == VALID_ROWS
	assert items[0] == "A"
	assert items[25] == "Z"
	assert items[26] == "AA"
	assert items[28] == "AC"
	assert items[98] == "CU"
	assert len(items) == len(VALID_ROWS) == 99
	assert "CV" not in items

def test_valid_rows():
	for row in ["A","Z","AA","CU"]:
		assert row in VALID_ROWS
	for bad_row in ["","CV","ABC","A1"]:
		assert bad_row not in VALID_ROWS

@mark.parametrize(
		"label, alpha, number",
		[
			( "A1"    , "A"  ,  1 ),
			( "B12"   , "B"  , 12 ),
			( "AA1"   , "AA" ,  1 ),
			( "XYZ96" , "XYZ", 96 ),
		]
	)
def test_split_alpha_and_number(label,alpha,number):
	assert split_alpha_and_number(label) == (alpha,number)

def test_split_alpha_and_no_number():
	alpha,number = split_alpha_and_number("XYZ")
	assert alpha=="XYZ"
	assert isnan(number)

@mark.parametrize( "bad_label", ["A 1","ü2","A.1"] )
def test_split_bad_alpha_and_number(bad_label):
	with raises(ValueError):
		split_alpha_and_number(bad_label)

@mark.parametrize(
		"well, row, col",
		[
			( "A1"   , "A"  ,  1 ),
			( "B12"  , "B"  , 12 ),
			( "AA1"  , "AA" ,  1 ),
		]
	)
def test_split_well_name(well,row,col):
	assert split_well_name(well) == (row,col)

@mark.parametrize("bad_well",["A","1","OD:600","CV2"])
def test_split_bad_well(bad_well):
	with raises(ValueError):
		split_well_name(bad_well)

@mark.parametrize(
		"label,result",
		[
			( "BLK"     , True  ),
			( "ABC"     , True  ),
			( "SPLC11"  , True  ),
			( "A"       , True  ),
			( "A1"      , False ),
			( "CU1"     , False ),
			( "STD 4"   , False ),
			( "CV1"     , True  ),
		]
	)
def test_is_sample_label_string(label,result):
	assert is_sample_label_string(label) == result

@mark.parametrize(
		"label,result",
		[
			( "BLK"     , True  ),
			( "SPLC11"  , True  ),
			( "CV12"    , True  ),
			( "CU12"    , False ),
			(("STD1" ,1), True  ),
			(("STD 1",4), False ),
			(("A1"   ,4), False ),
		]
	)
def test_is_sample_id(label,result):
	assert is_sample_id(label) == result

existing_channels = ["OD:600","YFP","CFP"]
@mark.parametrize(
		"string, name, channel",
		[
			( "Max V [OD:600]" , "Max V"     , "OD:600" ),
			( "Lagtime [YFP]"  , "Lagtime"   , "YFP"    ),
			( "R-Squared [CFP]", "R-Squared" , "CFP"    ),
		]
	)
def test_extract_channel(string,name,channel):
	assert extract_channel(string,existing_channels) == (name,channel)

@mark.parametrize(
		"string, existing_channels",
		[
			( "Max V [OD:600", existing_channels ),
			( "abc"          , existing_channels ),
			( "Lagtime [YFP]", ["OD:600"]        ),
		]
	)
def test_extract_bad_channel(string,existing_channels):
	with raises(ValueError):
		extract_channel(string,existing_channels)

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
		"string, number",
		[
			( "1"     ,    1),
			( "2.34"  , 2.34),
			( "-4.2"  , -4.2),
			( "OVRFLW",  inf),
			( "?????" ,  nan),
			( "<0.001",    0),
		]
	)
def test_parse_number(string,number):
	np.testing.assert_equal( parse_number(string), number )

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


