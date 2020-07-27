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

