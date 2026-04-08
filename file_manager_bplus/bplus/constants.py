# B+ Tree Order and derived constants
# ORDER=4 means each internal node can hold up to 3 keys and 4 children
# Each leaf node can hold up to 3 key-value pairs

ORDER = 4                    # B+ Tree order
MAX_KEYS = ORDER - 1         # Maximum keys per node = 3
MIN_KEYS = (ORDER // 2)      # Minimum keys for non-root nodes = 2
MAX_CHILDREN = ORDER         # Maximum children per internal node = 4
