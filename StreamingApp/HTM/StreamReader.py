
"""
Kafka based file based implementation of a record stream
"""

import os
import csv
import copy
import json
import sys


from nupic.data.field_meta import FieldMetaInfo, FieldMetaType, FieldMetaSpecial
from nupic.data import SENTINEL_VALUE_FOR_MISSING_DATA
from nupic.data.record_stream import RecordStreamIface
from nupic.data.utils import (intOrNone, floatOrNone, parseBool, parseTimestamp,
    serializeTimestamp, serializeTimestampNoMS, escape, unescape, parseSdr,
    serializeSdr, parseStringList, stripList)

# set this field before calling the nextRecordMethod/network.run method
data =0
mem =0

class kafkaRecordStream(RecordStreamIface):
  """
  The kafkaRecordStream iterates over the field names, types and specials and
  stores the information.

  :param streamID:
      CSV file name, input or output
  :param write:
      True or False, open for writing if True
  :param fields:
      a list of nupic.data.fieldmeta.FieldMetaInfo field descriptors, only
      applicable when write==True
  :param missingValues:
      what missing values should be replaced with?
  :param bookmark:
      a reference to the previous reader, if passed in, the records will be
      returned starting from the point where bookmark was requested. Either
      bookmark or firstRecord can be specified, not both. If bookmark is used,
      then firstRecord MUST be None.
  :param includeMS:
      If false, the microseconds portion is not included in the
      generated output file timestamp fields. This makes it compatible
      with reading in from Excel.
  :param firstRecord:
      0-based index of the first record to start reading from. Either bookmark
      or firstRecord can be specified, not both. If bookmark is used, then
      firstRecord MUST be None.

  """

  # Private: number of header rows (field names, types, special)
  _NUM_HEADER_ROWS = 3

  # Private: file mode for opening file for writing
  _FILE_WRITE_MODE = 'w'

  # Private: file mode for opening file for reading
  _FILE_READ_MODE = 'r'


  def __init__(self, streamName, write=False, fields=None, missingValues=None,
               bookmark=None, includeMS=True, firstRecord=None, names=None):
    super(kafkaRecordStream, self).__init__()

    # Only bookmark or firstRow can be specified, not both
    if bookmark is not None and firstRecord is not None:
      raise RuntimeError(
          "Only bookmark or firstRecord can be specified, not both")

    if fields is None:
      fields = []
    if missingValues is None:
      missingValues = ['']

    # We'll be operating on csvs with arbitrarily long fields
    size = 2**27
    csv.field_size_limit(size)

    self.name = streamName
    specials = []
    specials.append('')
    types = []
    types.append('float')
    
    if names is None:
	  names = []
	  names.append('cpu')
    elif len(names)==2:
	  specials.append('')
	  types.append('float')
	
	# We can't guarantee what system files are coming from, use universal
    # newlines
    self._fields = [FieldMetaInfo(*attrs)
                    for attrs in zip(names, types, specials)]
    self._fieldCount = len(self._fields)
    
    # Keep track on how many records have been read/written
    self._recordCount = 0

    # keep track of the current sequence
    self._currSequence = None
    self._currTime = None
    self._timeStampIdx = None
    self._sequenceIdIdx = None
    self._resetIdx = None
    self._categoryIdx = None
    self._learningIdx = None
    
    if self._timeStampIdx:
      assert types[self._timeStampIdx] == FieldMetaType.datetime
    if self._sequenceIdIdx:
      assert types[self._sequenceIdIdx] in (FieldMetaType.string,
                                            FieldMetaType.integer)
    if self._resetIdx:
      assert types[self._resetIdx] == FieldMetaType.integer
    if self._categoryIdx:
      assert types[self._categoryIdx] in (FieldMetaType.list,
                                          FieldMetaType.integer)
    if self._learningIdx:
      assert types[self._learningIdx] == FieldMetaType.integer

    # Convert the types to the actual types in order to convert the strings
    m = {FieldMetaType.integer: intOrNone,
         FieldMetaType.float: floatOrNone,
         FieldMetaType.boolean: parseBool,
         FieldMetaType.string: unescape,
         FieldMetaType.datetime: parseTimestamp,
         FieldMetaType.sdr: parseSdr,
         FieldMetaType.list: parseStringList}
    
    self._adapters = [m[t] for t in types]
    self._missingValues = missingValues

    # Dictionary to store record statistics (min and max of scalars for now)
    self._stats = None


  def __getstate__(self):
    d = dict()
    d.update(self.__dict__)
    return d


  def __setstate__(self, state):
    self.__dict__ = state
    self._file = None
    self._reader = None
    self.rewind()

  def printData(self):
    print("Data:" +str(data) + ", "+ +str(mem))

  def setData(self, dataRec, memRec=None):
	global data
	global mem
	data = dataRec
	mem = memRec
	
  def close(self):
    """
    Closes the stream.
    """
    if self._file is not None:
      self._file.close()
      self._file = None


  def rewind(self):
    """
    Put us back at the beginning of the file again.
    """
    # Reset record count, etc.
    self._recordCount = 0

  def grabStreamData(self):
	line = []
	global data
	global mem
	line.append(data)
	if mem is not None:
		line.append(mem)
	
	print("grabStreamData Called: "+str(line))
	return line
  
  def getNextRecord(self, useCache=True):
    """ Returns next available data record from the file.

    :returns: a data row (a list or tuple) if available; None, if no more
              records in the table (End of Stream - EOS); empty sequence (list
              or tuple) when timing out while waiting for the next record.
    """
    # Read the line
    try:
      line = self.grabStreamData()
      
    except StopIteration:
      if self.rewindAtEOF:
        if self._recordCount == 0:
          raise Exception("The source configured to reset at EOF but "
                          "'%s' appears to be empty" % self._filename)
        self.rewind()

      else:
        return None

    # Keep score of how many records were read
    self._recordCount += 1

    # Split the line to text fields and convert each text field to a Python
    # object if value is missing (empty string) encode appropriately for
    # upstream consumers in the case of numeric types, this means replacing
    # missing data with a sentinel value for string type, we can leave the empty
    # string in place
    record = []
    for i, f in enumerate(line):
      #print "DEBUG: Evaluating field @ index %s: %r" % (i, f)
      #sys.stdout.flush()
      if f in self._missingValues:
        record.append(SENTINEL_VALUE_FOR_MISSING_DATA)
      else:
        # either there is valid data, or the field is string type,
        # in which case the adapter does the right thing by default
        record.append(self._adapters[i](f))

    return record


  def appendRecord(self, record):
    """
    Saves the record in the underlying csv file.

    :param record: a list of Python objects that will be string-ified
    """
    print("appendRecord called")


  def appendRecords(self, records, progressCB=None):
    """
    Saves multiple records in the underlying storage.

    :param records: array of records as in
                    :meth:`~.FileRecordStream.appendRecord`
    :param progressCB: (function) callback to report progress
    """
    print("appendRecords called")
    

  def getBookmark(self):
    """
    Gets a bookmark or anchor to the current position.

    :returns: an anchor to the current position in the data. Passing this
              anchor to a constructor makes the current position to be the first
              returned record.
    """
    
    return None


  def recordsExistAfter(self, bookmark):
    """
    Returns whether there are more records from current position. ``bookmark``
    is not used in this implementation.

    :return: True if there are records left after current position.
    """
    return (self.getDataRowCount() - self.getNextRecordIdx()) > 0


  def seekFromEnd(self, numRecords):
    """
    Seeks to ``numRecords`` from the end and returns a bookmark to the new
    position.

    :param numRecords: how far to seek from end of file.
    :return: bookmark to desired location.
    """
    self._file.seek(self._getTotalLineCount() - numRecords)
    return self.getBookmark()


  def setAutoRewind(self, autoRewind):
    """
    Controls whether :meth:`~.FileRecordStream.getNextRecord` should
    automatically rewind the source when EOF is reached.

    :param autoRewind: (bool)

        - if True, :meth:`~.FileRecordStream.getNextRecord` will automatically rewind
          the source on EOF.
        - if False, :meth:`~.FileRecordStream.getNextRecord` will not automatically
          rewind the source on EOF.
    """
    self.rewindAtEOF = autoRewind


  def getStats(self):
    """
    Parse the file using dedicated reader and collect fields stats. Never
    called if user of :class:`~.FileRecordStream` does not invoke
    :meth:`~.FileRecordStream.getStats` method.

    :returns:
          a dictionary of stats. In the current implementation, min and max
          fields are supported. Example of the return dictionary is:

          .. code-block:: python

             {
               'min' : [f1_min, f2_min, None, None, fn_min],
               'max' : [f1_max, f2_max, None, None, fn_max]
             }

          (where fx_min/fx_max are set for scalar fields, or None if not)

    """

    # Collect stats only once per File object, use fresh csv iterator
    # to keep the next() method returning sequential records no matter when
    # caller asks for stats
    print("getStats called")
    return None


  def clearStats(self):
    """ Resets stats collected so far.
    """
    self._stats = None


  def getError(self):
    """
    Not implemented. CSV file version does not provide storage for the error
    information
    """
    return None


  def setError(self, error):
    """
    Not implemented. CSV file version does not provide storage for the error
    information
    """
    return


  def isCompleted(self):
    """ Not implemented. CSV file is always considered completed."""
    return True


  def setCompleted(self, completed=True):
    """ Not implemented: CSV file is always considered completed, nothing to do.
    """
    return


  def getFieldNames(self):
    """
    :returns: (list) field names associated with the data.
    """
    return [f.name for f in self._fields]


  def getFields(self):
    """
    :returns: a sequence of :class:`~.FieldMetaInfo`
              ``name``/``type``/``special`` tuples for each field in the stream.
    """
    if self._fields is None:
      return None
    else:
      return copy.copy(self._fields)


  def _updateSequenceInfo(self, r):
    """Keep track of sequence and make sure time goes forward

    Check if the current record is the beginning of a new sequence
    A new sequence starts in 2 cases:

    1. The sequence id changed (if there is a sequence id field)
    2. The reset field is 1 (if there is a reset field)

    Note that if there is no sequenceId field or resetId field then the entire
    dataset is technically one big sequence. The function will not return True
    for the first record in this case. This is Ok because it is important to
    detect new sequences only when there are multiple sequences in the file.
    """

    # Get current sequence id (if any)
    newSequence = False
    sequenceId = (r[self._sequenceIdIdx]
                  if self._sequenceIdIdx is not None else None)
    if sequenceId != self._currSequence:
      # verify that the new sequence didn't show up before
      if sequenceId in self._sequences:
        raise Exception('Broken sequence: %s, record: %s' % \
                        (sequenceId, r))

      # add the finished sequence to the set of sequence
      self._sequences.add(self._currSequence)
      self._currSequence = sequenceId

      # Verify that the reset is consistent (if there is one)
      if self._resetIdx:
        assert r[self._resetIdx] == 1
      newSequence = True

    else:
      # Check the reset
      reset = False
      if self._resetIdx:
        reset = r[self._resetIdx]
        if reset == 1:
          newSequence = True

    # If it's still the same old sequence make sure the time flows forward
    if not newSequence:
      if self._timeStampIdx and self._currTime is not None:
        t = r[self._timeStampIdx]
        if t < self._currTime:
          raise Exception('No time travel. Early timestamp for record: %s' % r)

    if self._timeStampIdx:
      self._currTime = r[self._timeStampIdx]


  def _getStartRow(self, bookmark):
    """ Extracts start row from the bookmark information
    """
    print("getStats called")


  def _getTotalLineCount(self):
    """ Returns:  count of ALL lines in dataset, including header lines
    """
    
    print("Total Count called!")
    # Flush the file before we open it again to count lines
    return sys.maxsize;


  def getNextRecordIdx(self):
    """
    :returns: (int) the index of the record that will be read next from
              :meth:`~.FileRecordStream.getNextRecord`.
    """
    return self._recordCount


  def getDataRowCount(self):
    """
    :returns: (int) count of data rows in dataset (excluding header lines)
    """
    numLines = self._getTotalLineCount()

    if numLines == 0:
      # this may be the case in a file opened for write before the
      # header rows are written out
      assert self._mode == self._FILE_WRITE_MODE and self._recordCount == 0
      numDataRows = 0
    else:
      numDataRows = numLines - self._NUM_HEADER_ROWS

    assert numDataRows >= 0

    return numDataRows


  def setTimeout(self, timeout):
    pass


  def flush(self):
    """
    Flushes the file.
    """
    if self._file is not None:
      self._file.flush()


  def __enter__(self):
    """Context guard - enter

    Just return the object
    """
    return self


  def __exit__(self, yupe, value, traceback):
    """Context guard - exit

    Ensures that the file is always closed at the end of the 'with' block.
    Lets exceptions propagate.
    """
    self.close()


  def __iter__(self):
    """Support for the iterator protocol. Return itself"""
    return self


  def next(self):
    """Implement the iterator protocol """
    record = self.getNextRecord()
    if record is None:
      raise StopIteration

    return record

