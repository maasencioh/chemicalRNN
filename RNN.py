from utils import get_metadata #, get_stream, track_best, MainLoop
from config import config

# Load config parameters
locals().update(config)

# DATA
ix_to_char, char_to_ix, vocab_size = get_metadata(hdf5_file)

print ix_to_char
print char_to_ix
print vocab_size