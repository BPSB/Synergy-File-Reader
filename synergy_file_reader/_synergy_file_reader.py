from synergy_file_reader.tools import (
		split_well_name, extract_channel, is_sample_id,
		parse_number, parse_time, parse_timestamp,
		row_iter, VALID_ROWS,
		LineBuffer,
		wrap_variant
	)
import numpy as np
from datetime import datetime
from warnings import warn

format_parsers = [parse_time, parse_number]

timescales = {
		"seconds":        1,
		"minutes":       60,
		"hours"  :    60*60,
		"days"   : 24*60*60,
	}

IGNORED_CHANNELS = { "Count", "Mean", "Std Dev", "CV (%)" }

class FormatMismatch(Exception): pass
class RepeatingData(Exception): pass

def format_assert(condition):
	if not condition:
		raise FormatMismatch

def parse_cols(cols):
	cols = [ int(col) for col in cols ]
	format_assert( cols )
	format_assert( cols==list(range(1,len(cols)+1)) )
	return cols

def assert_temperature_label(label,channel):
	format_assert( label in [ "T° "+channel, "T "+channel ] )

class ValueError_to_FormatMismatch(object):
	"""
		Context manager that catches all ValueErrors within the context and reraises them as FormatMismatches.
	"""
	def __enter__(self):
		pass
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		if exc_type:
			if issubclass(exc_type,ValueError):
				raise FormatMismatch from exc_value

class Attempt(object):
	def __init__(self,parser,parent):
		self.parser = parser
		self.parent = parent
	
	def __enter__(self):
		return self.parser
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		if exc_type:
			if issubclass(exc_type,ValueError):
				return True
		else:
			self.parent.success = True

class TryFormats(object):
	def __init__(self):
		self.success = False
	
	def __iter__(self):
		for format_parser in format_parsers:
			yield Attempt(format_parser,self)
			if self.success:
				break
		else:
			raise FormatMismatch

class SynergyIndexable(object):
	def __init__(self,sample_ids=None):
		self.data = {}
		self.rows = []
		self.cols = []
		self.sample_ids = sample_ids
	
	def _add_row(self,row):
		if row not in self.rows:
			self.rows.append(row)
	
	def _add_col(self,col):
		if col not in self.cols:
			self.cols.append(col)
	
	def keys(self):
		return self.data.keys()
	
	def values(self):
		return self.data.values()
	
	def _normalise_well_index(self,index):
		"""
		Returns an iterable of normalised indices from the given index.
		A normalised index consists of a row, a col, and the further elements of `index`.
		"""
		
		# Avoid string as single index being interpreted as iterable:
		index = [index] if isinstance(index,str) else list(index)
		
		if (
				    len(index)>=2
				and (index[0] in VALID_ROWS)
				and isinstance(index[1],int)
			):
				row,col = index[:2]
				row = row.upper()
				yield (row,col,*index[2:])
		elif is_sample_id(index[0]):
			if self.sample_ids is None:
				raise ValueError("No layout information available.")
			results = self.sample_ids[index[0]]
			for result in results:
				yield (*result,*index[1:])
		else:
			try:
				row,col = split_well_name(index[0].upper())
			except ValueError:
				raise ValueError("Not a valid index.")
			else:
				yield (row,col,*index[1:])
	
	def _convert_indices(self,index):
		for row,col,*residual in self._normalise_well_index(index):
			if residual:
				raise ValueError("Too many indices.")
			yield row,col
	
	def __setitem__(self,index,result):
		indices = list(self._convert_indices(index))
		if len(indices) != 1:
			raise ValueError("Index is not unique")
		if indices[0] in self.keys():
			raise RepeatingData
		
		row,col,*residual = indices[0]
		self._add_row(row)
		self._add_col(col)
		self.data[(row,col,*residual)] = result
	
	def __getitem__(self,index):
		indices = list(self._convert_indices(index))
		if len(indices)==1:
			return self.data[indices[0]]
		else:
			return [ self.data[index] for index in indices ]

class SynergyResult(SynergyIndexable):
	"""
	A single well- and channel-wise result.
	
	You can index this in different ways, using the well F7 for the channel `"OD"` as an example:
	
	* Row letter, column number, and channel separately: `result["F",7,"OD"]`
	* Well identifier in one string: `result["F7","OD"]`
	* If there is only one channel, you do not need to specify it: `result["F7"]`
	* If your plate contains information on sample IDs, you can also use those for indexing: `result["SPL55","OD"]`. If the sample ID is not unique, a list of the respective content of all matching wells will be returned.
	
	It comes with the following attributes and methods:
	
	* `rows` and `cols` are lists of the row letters and column numbers, respectively.
	* `channels` is a list of all channels for which recordings exists.
	* `keys` and `values` are methods similar to those for dictionaries, returning iterables of all keys and values respectively.
	* If your plate contains information on sample IDs, `sample_ids` contains the mappin of sample IDs to wells.
	"""
	
	def __init__(self,sample_ids=None):
		super().__init__(sample_ids)
		self.channels = []
	
	def _add_channel(self,channel):
		if channel not in self.channels:
			self.channels.append(channel)
	
	def _convert_indices(self,index):
		for row,col,*residual in self._normalise_well_index(index):
			if len(residual)==0:
				if len(self.channels)==1:
					channel = self.channels[0]
				else:
					raise ValueError("You must specify a channel as there is more than one in this read.")
			elif len(residual)==1:
				channel = residual[0]
			else:
				raise ValueError("Too many indices.")
			
			yield row,col,channel
	
	def __setitem__(self,index,result):
		if index[-1] not in IGNORED_CHANNELS:
			super().__setitem__(index,result)
			_,_,channel = next(self._convert_indices(index))
			self._add_channel(channel)
		else:
			warn(f"Columns/rows, etc. headed with any of {IGNORED_CHANNELS} will be ignored and not parsed.")

class SynergyPlate(SynergyResult):
	"""
	Data for a single plate.
	
	Raw data can be accessed by indexing this object directly like a `SynergyResult`.
	
	This usally comes with the following methods and attributes:
	
	* `rows` and `cols` are lists of the row letters and column numbers, respectively.
	* `channels` is a list of all channels for which recordings exists.
	* `keys` and `values` are methods similar to those for dictionaries, returning iterables of all keys and values respectively.
	* `times` is a dictionary specifying the times of measurements (in seconds) for each channel.
	* `temperature_range` is contains the minimal and maximal temperature specified in the file. This almost always contains some meaningful information.
	* `temperatures` is a dictionary specifying the temperatures at the times of measurements for each channel. This is only not empty if the file specifies the information.
	* `metadata` is a dictionary of metadata like the time of the measurement, procedure details, file paths, and information about the device.
	* `results` is a dictionary of `SynergyResult`. These are usually aggregated estimates by the plate-reader software such as of the growth rate, lag time, etc.
	* `gains` is a dictonary containing the automatic gains determined for each channel, if such exist. Otherwise it’s empty.
	* `plot` allows to quickly plot the data and has an extensive documentation.
	"""
	def __init__(self):
		super().__init__()
		self.metadata = {}
		self.times = None
		self.temperatures = {}
		self.results = {}
		self.gains = {}
		self.sample_ids = None
		self.layout = None
	
	def _add_time(self,time,channel):
		if self.times is None:
			self.times = {}
		self._add_channel(channel)
		if channel in self.times:
			if time != self.times[channel][-1]:
				assert time > self.times[channel][-1]
				self.times[channel] = np.append(self.times[channel],time)
		else:
			self.times[channel] = np.array([time])
	
	def _add_temperature(self,time,channel,temp):
		self._add_time(time,channel)
		self._add_channel(channel)
		try:
			self.temperatures[channel] = np.append(self.temperatures[channel],temp)
		except KeyError:
			self.temperatures[channel] = np.array([temp])
		else:
			assert len(self.temperatures[channel])==len(self.times[channel])
	
	def _add_gain(self,channel,value):
		self._add_channel(channel)
		if channel in self.gains:
			raise ValueError("Duplicate gain value")
		self.gains[channel] = value
	
	def _add_raw_result(self,channel,row,col,value,time=None):
		if time is not None:
			self._add_time(time,channel)
			if (row,col,channel) in self.keys():
				self.data[row,col,channel] = np.append(self[row,col,channel],value)
				assert len(self[row,col,channel])==len(self.times[channel])
			else:
				self[row,col,channel] = np.array([value])
		else:
			self[row,col,channel] = value
	
	def _add_result(self,name,row,col,value):
		if isinstance(name,tuple):
			self._add_raw_result(name,row,col,value)
			return
		
		try:
			key,channel = extract_channel(name,self.channels)
		except ValueError:
			self._add_raw_result(name,row,col,value)
			return
		
		if key not in self.results:
			self.results[key] = SynergyResult(self.sample_ids)
		self.results[key][row,col,channel] = value
	
	def _add_metadata(self,**new_metadata):
		if "Min Temperature" in new_metadata:
			assert "Max Temperature" in new_metadata
			self._update_temperature_range(
					parse_number(new_metadata.pop("Min Temperature")),
					parse_number(new_metadata.pop("Max Temperature")),
				)
		
		try:
			act_temp = parse_number(new_metadata.pop("Actual Temperature"))
		except KeyError:
			pass
		else:
			self._update_temperature_range(act_temp,act_temp)
		
		# After Min and Max Temperatures as these can indeed repeat:
		if any( key in self.metadata for key in new_metadata ):
			raise RepeatingData
		
		if "Date" in new_metadata:
			assert "Time" in new_metadata
			date_and_time = new_metadata.pop("Date") + " " + new_metadata.pop("Time")
			for datetime_format in [
						"%m/%d/%Y %I:%M:%S %p",
						"%Y-%m-%d %H:%M:%S",
				]:
				try:
					self.metadata["datetime"] = datetime.strptime(
						date_and_time,
						datetime_format,
					)
				except ValueError:
					continue
				else:
					break
			else:
				raise ValueError(f"{date_and_time} does not match any implemented time format.")
		
		for key,value in new_metadata.items():
			if key=="Software Version":
				value = tuple( int(x) for x in value.split(".") )
			
			self.metadata[key] = value
	
	def _update_temperature_range(self,min_temp,max_temp):
		if not hasattr(self,"_temperature_range"):
			self._temperature_range = (np.inf,-np.inf)
		self._temperature_range = (
				min(self._temperature_range[0],min_temp),
				max(self._temperature_range[1],max_temp),
			)

	@property
	def temperature_range(self):
		if hasattr(self,"_temperature_range"):
			return self._temperature_range
		else:
			all_temps = [
					temp
					for temps in self.temperatures.values()
					for temp in temps
				]
			return min(all_temps),max(all_temps)
	
	def __repr__(self):
		return(f"SynergyPlate( {self.metadata}, {self.times}, {self.temperatures}, {self.data}, {self.results} )")
	
	def plot(self, *,
			channels=None, colours=None,
			xlim=None, ylim=None,
			baseline=0,
			log_y=True, plot_args={},
			timescale = None,
			label_pad=20, label_size="xx-large",
			reference=None, reference_plot_args={},
		):
		"""
		plots time series of the raw data using Matplotlib.
		
		This is a service function to quickly obtain a decent plot. It does not cover all potential use cases and is not suited as basis for extensive customisations. If you want a starting point for the latter, have a look at `this example <https://github.com/BPSB/synergy_file_reader/tree/master/examples/explicit_plot.py>`_.
		
		Returns
		-------
		
		figure : Matlotlib figure object
		
		axess : array of Matplotlib axes objects
		
		Parameters
		----------
		
		channels : iterable of keys or None
			The channels to be plotted. If `None`, all channels will be plotted.
		
		colours: iterable of colour names or None
			The colours to use for the respective channels. If `None`, Matplotlib’s default colour cycle will be used.
		
		xlim, ylim: pair of numbers or None
			The ranges of the plot. If `None` this will be chosen automatically by Matplotlib.
			
		baseline: number or array
			This will be subtracted from the values of all time series before plotting (including the reference).
		
		log_y: boolean
			Whether the ordinate should be logarithmic.
		
		plot_args: dictionary
			Further keyword arguments to be passed to every plot (except the reference).
		
		timescale: one of "seconds", "minutes", "hours", "days", or None
			Which timescale to use for labelling. If `None`, this will be guessed.
		
		label_pad: number
			Padding of row and column labels.
		
		label_size: Matplotlib font size
			Size of row and column labels.
		
		reference: array or None
			A reference time series to be plotted below all time series.
			The times used will be the ones for the first channel.
		
		reference_plot_args: dictionary
			Keyword arguments to be passed to the plot command of the reference time series. This includes `color` and `label`.
		"""
		
		from matplotlib.pyplot import subplots
		
		if channels is None:
			channels = self.channels
		
		if colours is None:
			colours = [ None for channel in channels ]
		
		if timescale is None:
			t_max = self.times[-1] if xlim is None else xlim[1]
			candidates = ( ts for ts in timescales if 2*timescales[ts]<t_max )
			timescale = max( candidates, key = lambda ts: timescales[ts] )
		
		fig,axess = subplots(
				len(self.rows), len(self.cols),
				figsize=(15,10),
				sharex="all", sharey="all"
			)
		
		for axess_row,row in zip(axess,self.rows):
			for axes,col in zip(axess_row,self.cols):
				handles = []
				if reference is not None:
					handles.extend(axes.plot(
						self.times[channels[0]]/timescales[timescale],
						reference - baseline,
						**reference_plot_args,
					 ))
				for channel,colour in zip(channels,colours):
					handles.extend(axes.plot(
							self.times[channel]/timescales[timescale],
							self[row,col,channel] - baseline,
							color = colour,
							label = channel,
							**plot_args,
						))
		
		if log_y:
			axes.set_yscale("log")
		if xlim is not None:
			axes.set_xlim( *(np.array(xlim)/timescales[timescale]) )
		if ylim is not None:
			axes.set_ylim(*ylim)
		for axes,col in zip(axess[-1],self.cols):
			axes.set_xlabel(timescale)
		
		if len(handles)==1:
			for axes in axess[:,0]:
				axes.set_ylabel(channels[0])
		else:
			fig.legend(handles=handles,loc="center right")
		
		# Subplot labelling thanks to https://stackoverflow.com/a/25814386/2127008
		
		for axes,col in zip(axess[0],self.cols):
			axes.annotate(
					col,
					xy=(0.5,1), xycoords='axes fraction',
					xytext=(0,label_pad), textcoords='offset points',
					size=label_size, ha='center', va='baseline',
				)

		for axes,row in zip(axess[:,0],self.rows):
			axes.annotate(
					row,
					xy=(0,0.5), xycoords=axes.yaxis.label,
					xytext=(-label_pad,0), textcoords='offset points',
					size=label_size, ha='center', va='center',
				)
		
		return fig,axess

class SynergyFile(list):
	"""
		Represents the contents of a Synergy file. For most practical purposes, you can treat this like a list of `SynergyPlate`. Often this list contains only one plate.
		
		Parameters
		----------
		filename : string
			The location of the filename from which to read the data.
		separator : string
			The separator character used in the file.
		encoding : string specifying a supported encoding
			The encoding of the file. This cannot be automatically detected.
		verbose : boolean
			whether to detail information about the parsing process. Mostly useful for debugging.
	"""
	def __init__(self,
			filename,
			separator="\t",
			encoding="iso-8859-1",
			verbose=False
		):
		super().__init__()
		self.sep = separator
		self._new_plate()
		
		self.verbose = verbose
		
		with open(filename,"r",encoding=encoding) as f:
			self._line_buffer = LineBuffer(f.read().splitlines())
		
		self._parse_file()
	
	def report(self,message,newline=True):
		if self.verbose:
			print(
					message,
					end = "\n" if newline else "",
				)
	
	def _parse_file(self):
		while self._line_buffer:
			for parser in (
					self._parse_raw_data_matrix,
					self._parse_raw_data_row,
					wrap_variant(self._parse_raw_data_row,"blank"),
					self._parse_raw_data_column,
					wrap_variant(self._parse_raw_data_column,"blank"),
					self._parse_results_matrix,
					wrap_variant(self._parse_results_row,"well_id_and_conc"),
					wrap_variant(self._parse_results_row,"well_id"),
					self._parse_results_row,
					wrap_variant(self._parse_results_column,"well_id_and_conc"),
					wrap_variant(self._parse_results_column,"well_id"),
					self._parse_results_column,
					self._parse_single_matrix,
					self._parse_single_row,
					self._parse_single_column,
					self._parse_other_metadata,
					self._parse_gain_values,
					self._parse_metadata,
					self._parse_layout,
					wrap_variant(self._parse_layout,"conc"),
					self._parse_spectrum_column,
					self._parse_blank_data,
				):
				try:
					with self._line_buffer as line_iter:
						parser(line_iter)
				except FormatMismatch as e:
					continue
				except RepeatingData:
					self.report("Found repeating data with {parser__name__}; created new plate.")
					self._new_plate()
					break
				else:
					self.report(f"Successful {parser.__name__:<22}")
					break
			else:
				raise ValueError("File does not appear to have a valid or implemented format.")
	
	def _new_plate(self):
		self.append(SynergyPlate())
	
	def _parse_metadata(self,line_iter):
		new_metadata = {}
		# looping over lines here (instead doing one at a time) to:
		# • get time and date together
		# • raise RepeatingData as early as possible
		
		for line in line_iter:
			if line == "":
				break
			
			format_assert( line.count(self.sep) == 1 )
			key,_,value = line.partition(self.sep)
			if key.endswith(":"):
				key = key[:-1]
			new_metadata[key] = value
		
		self[-1]._add_metadata(**new_metadata)
	
	def _parse_other_metadata(self,line_iter):
		header = next(line_iter)
		try:
			attribute = {
				"Procedure Details": "procedure",
				"Curve Fitting Results": "curve_fitting",
				"DRCurve Fitting Results": "dr_curve_fitting",
				"DRCurve Interpolations": "dr_curve_interpolations",
			}[header]
		except KeyError:
			raise FormatMismatch
		
		format_assert( next(line_iter) == "" )
		
		content = []
		for line in line_iter:
			if line=="": break
			content.append(line.replace(self.sep,"\t"))
		self[-1]._add_metadata( **{attribute: "\n".join(content)} )
	
	def _parse_gain_values(self,line_iter):
		format_assert( next(line_iter) == "Automatic gain values\t " )
		gains = []
		for line in line_iter:
			if line=="": break
			label,value = line.split(self.sep)
			Gain,_,channel = label.partition("(")
			format_assert( Gain == "Gain" )
			format_assert( channel.endswith(")") )
			channel = channel[:-1]
			with ValueError_to_FormatMismatch():
				value = float(value)
			gains.append((channel,value))
		
		for channel,value in gains:
			self[-1]._add_gain(channel,value)
	
	def _parse_results_matrix(self,line_iter):
		format_assert( next(line_iter) == "Results" )
		
		with ValueError_to_FormatMismatch():
			empty,*cols = next(line_iter).split(self.sep)
			cols = parse_cols(cols)
		format_assert( empty == "" )
		
		results = []
		row = None
		expected_rows = row_iter()
		for line in line_iter:
			if line=="": break
			new_row,*numbers,name = line.split(self.sep)
			
			if new_row:
				format_assert( new_row == next(expected_rows) )
				row = new_row
			format_assert( row is not None )
			
			for attempt in TryFormats():
				with attempt as format_parser:
					numbers = [ format_parser(number) for number in numbers ]
			
			results.append((row,numbers,name))
		
		for row,numbers,name in results:
			for col,number in zip(cols,numbers):
				self[-1]._add_result(name,row,col,number)
	
	def _parse_results_row(self,line_iter,variant=""):
		format_assert( next(line_iter) == "Results" )
		format_assert( next(line_iter) == "" )
		
		if variant=="well_id":
			with ValueError_to_FormatMismatch():
				Well_ID,Well,*names = next(line_iter).split(self.sep)
			format_assert( Well_ID=="Well ID" )
		elif variant=="well_id_and_conc":
			with ValueError_to_FormatMismatch():
				Well_ID,Well,Concdil,*names = next(line_iter).split(self.sep)
			format_assert( Well_ID=="Well ID" )
			format_assert( Concdil=="Conc/Dil" )
		else:
			with ValueError_to_FormatMismatch():
				Well,*names = next(line_iter).split(self.sep)
		format_assert( Well=="Well" )
		
		results = []
		well_id = None
		for line in line_iter:
			if line=="": break
			
			if variant=="well_id":
				new_well_id,well,*numbers = line.split(self.sep)
				well_id = new_well_id or well_id
				format_assert( well_id == self[-1].layout[well] )
			elif variant=="well_id_and_conc":
				new_well_id,well,conc,*numbers = line.split(self.sep)
				well_id = new_well_id or well_id
				if conc:
					format_assert( (well_id,parse_number(conc)) == self[-1].layout[well] )
				else:
					format_assert( well_id == self[-1].layout[well] )
			else:
				well,*numbers = line.split(self.sep)
			
			with ValueError_to_FormatMismatch():
				row,col = split_well_name(well)
			
			format_assert( len(names)==len(numbers) )
			for name,number in zip(names,numbers):
				for attempt in TryFormats():
					with attempt as format_parser:
						number = format_parser(number)
				results.append((name,row,col,number))
		
		for name,row,col,number in results:
			self[-1]._add_result(name,row,col,number)
	
	def _parse_results_column(self,line_iter,variant=""):
		format_assert( next(line_iter) == "Results" )
		format_assert( next(line_iter) == "" )
		
		if variant.startswith("well_id"):
			with ValueError_to_FormatMismatch():
				Well_ID,*ids,last = next(line_iter).split(self.sep)
			format_assert( Well_ID == "Well ID" )
			format_assert( last == "" )
		
		with ValueError_to_FormatMismatch():
			Well,*wells,last = next(line_iter).split(self.sep)
			wells = [ split_well_name(well) for well in wells ]
		format_assert( Well == "Well" )
		format_assert( last == "" )
		
		if variant == "well_id_and_conc":
			with ValueError_to_FormatMismatch():
				concdil,*concs,last = next(line_iter).split(self.sep)
			format_assert( concdil == "Conc/Dil" )
			format_assert( last == "" )
		
		results = []
		for line in line_iter:
			if line=="": break
			name,*numbers,last = line.split(self.sep)
			format_assert( name != "Conc/Dil" )
			format_assert( len(wells) == len(numbers) )
			format_assert( last == "" )
			for attempt in TryFormats():
				with attempt as format_parser:
					numbers = [ format_parser(number) for number in numbers ]
			
			results.append((name,numbers))
		
		for name,numbers in results:
			for (row,col),number in zip(wells,numbers):
				self[-1]._add_result(name,row,col,number)
	
	def _parse_raw_data_column(self,line_iter,variant=""):
		channel = next(line_iter)
		format_assert( self.sep not in channel )
		format_assert( next(line_iter) == "" )
		
		if variant=="blank":
			format_assert( channel.startswith("Blank ") )
			with ValueError_to_FormatMismatch():
				Time,*wells = next(line_iter).split(self.sep)
		else:
			with ValueError_to_FormatMismatch():
				Time,Temp,*wells = next(line_iter).split(self.sep)
			assert_temperature_label(Temp,channel)
		format_assert( Time == "Time" )
		
		results = []
		for line in line_iter:
			if line=="": break
			with ValueError_to_FormatMismatch():
				if variant=="blank":
					time,*numbers = line.split(self.sep)
					temperature = np.nan
				else:
					time,temperature,*numbers = line.split(self.sep)
					temperature = parse_number(temperature)
				numbers = [ parse_number(number) for number in numbers ]
				time = parse_time(time)
			format_assert( len(numbers) == len(wells) )
			results.append((time,temperature,numbers))
		
		for time,temperature,numbers in results:
			if time==0 and all(np.isnan(numbers)):
				continue
			if variant!="blank":
				self[-1]._add_temperature(time,channel,temperature)
			for well,number in zip(wells,numbers):
				self[-1]._add_raw_result(channel,*split_well_name(well),number,time)
	
	def _parse_raw_data_row(self,line_iter,variant=""):
		channel = next(line_iter)
		format_assert( self.sep not in channel )
		format_assert( next(line_iter) == "" )
		
		with ValueError_to_FormatMismatch():
			label,*times,last = next(line_iter).split(self.sep)
		format_assert( last == "" )
		format_assert( label == "Time" )
		with ValueError_to_FormatMismatch():
			times = [ parse_time(time) for time in times ]
		
		if variant == "blank":
			temperatures = np.full_like(times,np.nan)
		else:
			with ValueError_to_FormatMismatch():
				label,*temperatures,last = next(line_iter).split(self.sep)
				temperatures = [ parse_number(temperature) for temperature in temperatures ]
			format_assert( last == "" )
				
			assert_temperature_label(label,channel)
			format_assert( len(temperatures) == len(times) )
		
		results = []
		wells = []
		for line in line_iter:
			if line=="": break
			with ValueError_to_FormatMismatch():
				well,*numbers,last = line.split(self.sep)
				numbers = [ parse_number(number) for number in numbers ]
				split_well_name(well)
			format_assert( last == "" )
			format_assert( len(numbers) == len(times) )
			wells.append(well)
			results.append(numbers)
		
		for i,(time,temperature,*numbers) in enumerate(zip(times,temperatures,*results)):
			if i>0 and time==0:
				break
			if variant != "blank":
				self[-1]._add_temperature(time,channel,temperature)
			for well,number in zip(wells,numbers):
				self[-1]._add_raw_result(channel,*split_well_name(well),number,time)
	
	def _parse_raw_data_matrix(self,line_iter):
		channel, _, timestamp = next(line_iter).partition(" - ")
		with ValueError_to_FormatMismatch():
			number,time = parse_timestamp(timestamp)
			format_assert( (number,time) == parse_timestamp(next(line_iter)) )
			empty,*cols = next(line_iter).split(self.sep)
			format_assert( empty == "" )
			cols = parse_cols(cols)
		
		results = []
		for line,expected_row in zip(line_iter,row_iter()):
			if line=="": break
			row,*numbers,label = line.split(self.sep)
			format_assert( len(numbers) == len(cols) )
			format_assert( row == expected_row )
			format_assert( label == f"{channel} Read#{number}" )
			with ValueError_to_FormatMismatch():
				numbers = [ parse_number(number) for number in numbers ]
			results.append((row,numbers))
		
		if time==0 and number>0:
			for _,numbers in results:
				format_assert( all(np.isnan(numbers)) )
		else:
			for row,numbers in results:
				for col,number in zip(cols,numbers):
					self[-1]._add_raw_result(channel,row,col,number,time)
	
	def _parse_single_matrix(self,line_iter):
		channel = next(line_iter)
		format_assert( self.sep not in channel )
		
		with ValueError_to_FormatMismatch():
			empty,*cols = next(line_iter).split(self.sep)
			cols = parse_cols(cols)
		format_assert( empty == "" )
		
		results = []
		for line,expected_row in zip(line_iter,row_iter()):
			if line=="": break
			with ValueError_to_FormatMismatch():
				row,*numbers,label = line.split(self.sep)
			format_assert( label == channel )
			format_assert( row == expected_row )
			
			for attempt in TryFormats():
				with attempt as format_parser:
					numbers = [ format_parser(number) for number in numbers ]
			
			results.append((row,numbers))
		
		for row,numbers in results:
			for col,number in zip(cols,numbers):
				self[-1]._add_result(channel,row,col,number)
	
	def _parse_single_row(self,line_iter):
		channel = next(line_iter)
		format_assert( self.sep not in channel )
		format_assert( next(line_iter) == "" )
		format_assert( next(line_iter) == "Well"+self.sep+channel )
		
		results = []
		for line in line_iter:
			if line=="": break
			well,number = line.split(self.sep)
			for attempt in TryFormats():
				with attempt as format_parser:
					number = format_parser(number)
			with ValueError_to_FormatMismatch():
				row,col = split_well_name(well)
			results.append((row,col,number))
		
		for row,col,number in results:
			self[-1]._add_result(channel,row,col,number)
	
	def _parse_single_column(self,line_iter):
		channel = next(line_iter)
		format_assert( self.sep not in channel )
		format_assert( next(line_iter) == "" )
		
		with ValueError_to_FormatMismatch():
			Well,*wells,last = next(line_iter).split(self.sep)
			wells = [ split_well_name(well) for well in wells ]
		format_assert( Well == "Well" )
		format_assert( last == "" )
		
		channel_2,*numbers,last = next(line_iter).split(self.sep)
		format_assert( last == "" )
		format_assert( channel_2 == channel )
		for attempt in TryFormats():
			with attempt as format_parser:
				numbers = [ parse_number(number) for number in numbers ]
		
		try:
			format_assert( next(line_iter) == "" )
		except StopIteration:
			pass
		
		for (row,col),number in zip(wells,numbers):
			self[-1]._add_result(channel,row,col,number)
	
	def _parse_layout(self,line_iter,variant=""):
		format_assert( next(line_iter) == "Layout" )
		
		with ValueError_to_FormatMismatch():
			empty,*cols = next(line_iter).split(self.sep)
			cols = parse_cols(cols)
		format_assert( empty == "" )
		
		layout = SynergyIndexable()
		sample_ids = {}
		expected_rows = row_iter()
		
		while True:
			line = next(line_iter)
			if line=="": break
			
			row  ,*labels ,well_id = line.split(self.sep)
			format_assert( row == next(expected_rows) )
			format_assert( empty == "" )
			if variant=="conc":
				empty,*condils,concdil = next(line_iter).split(self.sep)
				format_assert( well_id == "Well ID" )
				format_assert( concdil == "Conc/Dil" )
				
				with ValueError_to_FormatMismatch():
					condils = [ parse_number(condil) for condil in condils ]
				
				ids = [
						label if np.isnan(condil) else (label.partition(":")[0],condil)
						for label,condil in zip(labels,condils)
					]
			else:
				assert variant == ""
				ids = labels
			
			for sample_id,col in zip(ids,cols):
				layout[row,col] = sample_id
				try:
					sample_ids[sample_id].append((row,col))
				except KeyError:
					sample_ids[sample_id] = [(row,col)]
		
		self[-1].layout = layout
		self[-1].sample_ids = sample_ids
	
	def _parse_blank_data(self,line_iter):
		first_line = next(line_iter)
		format_assert( "[Blank " in first_line )
		format_assert( next(line_iter) == "" )
		for line in line_iter:
			if line=="": break
		
		warn("Data calculated from blanks will be ignored and not parsed.")
	
	def _parse_spectrum_column(self,line_iter):
		channel,_,spectrum = next(line_iter).partition(":")
		format_assert( spectrum == "Spectrum" )
		format_assert( self.sep not in channel )
		format_assert( next(line_iter) == "" )
		
		with ValueError_to_FormatMismatch():
			Wavelength,*wells = next(line_iter).split(self.sep)
			wells = [ split_well_name(well) for well in wells ]
		format_assert( Wavelength == "Wavelength" )
		
		results = []
		for line in line_iter:
			if line=="": break
			wavelength,*numbers = line.split(self.sep)
			with ValueError_to_FormatMismatch():
				wavelength = int(wavelength)
				numbers = [ parse_number(number) for number in numbers ]
			results.append((wavelength,numbers))
		
		for wavelength,numbers in results:
			for (row,col),number in zip(wells,numbers):
				self[-1]._add_result( (channel,wavelength), row, col, number )

