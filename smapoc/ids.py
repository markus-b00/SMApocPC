
# messaging ids

SELFTEST_SMAPOC = 1
SELFTEST_FORCE = 2
SELFTEST_LASER = 3
SELFTEST_WEBCAM = 4

# signal receiving
FROM_LASER = 11
FROM_FORCE = 12
FROM_SMAPOC = 13
FROM_WEBCAM = 14



# device IDs
DEV_LASER = 20
DEV_FORCE = 21
DEV_WEBCAM = 22
DEV_SMAPOC = 23


# mapping channel name to power vector order # ch2 was broken
CHANNEL_MAPPING = {'CH1': 0,
                   'CH2': 1,
                   'CH3': 2,
                   'CH4': 3,
                   'CH5': 4,
                   'CH6': 5}

# SMAPOC in openloop = current or closed loop == POWER
CURRENT = 3
POWER = 2