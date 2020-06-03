#-Andrew Speers

from csv import reader
import sys
import struct

"""
This data structure is a dictionary of dictionaries.
Each outer dictionary is labelled for a specific ID of record we're taking signals from.
Each inner dictionary is a key value pair of a control string to a list of timestamped values.

The control string is formatted as:
Character 1 gives the offset from the D0 column to begin reading the value
Character 2 gives whether the value is signed, unsigned, or a float
Character 3 gives the size of the value, so how many D arguments to read in at once
Character 4 if present gives the range of values to map down to, where t means [-30,30] and s means [-60,60]

The element of each list is itself a list, a pair of [time, actual_value].
"""
X = {
    "07E3" : {
        '0s2t' : [], #Roll axis input,  2 byte signed
        '2s2t': [], #Pitch axis input, 2 byte signed
        '4s2s': [], #Yaw axis input,   2 byte signed
        '6u2': []  #Hover throttle,   2 byte unsigned
    },
    "07E4" : {
        '0u1' : [], #Prop spin switch, 1 byte unsigned
        '2s2': []  #Pusher throttle,  2 byte signed
    },
    "0001" : {
        '0f4' : []  #Pitch angle,      4 byte float
    },
    "0002" : {
        '0f4' : []  #Ptich rate,       4 byte float
    },
    "0003" : {
        '0f4' : []  #Roll angle,       4 byte float
    },
    "0004" : {
        '0f4' : []  #Roll rate,        4 byte float
    },
    "0005" : {
        '0f4' : []  #Yaw angle,        4 byte float
    },
    "0006" : {
        '0f4' : []  #Yaw rate,         4 byte float
    }
}

with open(sys.argv[1], 'r') as the_file:
    iterator = reader(the_file, delimiter=';')
    for row in iterator:
        if len(row) < 5: #skipping unreadable lines
            continue
        row_id = row[5]
        if row_id not in X: #skipping the header and records from signals we don't care about
            continue
        time = float(row[1]) / 1000 #csv gives time in ms and we graph in s


        for I in X[row_id]:
            offset = int(I[0]) + 8
            kind   = I[1]
            size   = int(I[2])
            x = bytes.fromhex(''.join(row[offset:offset + size]))

            if kind == 'f':
                X[row_id][I].append(
                    [time, struct.unpack('>f', x)]
                )
            else:
                x = int.from_bytes(x, byteorder='big', signed=(kind == 's'))
                #Linear transformation if necessary
                if len(I) == 4:
                    OldRange = 32768 + 32767
                    NewRange = 60 if I[3] == 't' else 120
                    x = (((x - (-32767)) * NewRange) / OldRange) + (-30 if I[3] == 't' else -60)

                X[row_id][I].append(
                    [time, x]
                )

#Diagnostic information
for x in X:
    for y in X[x]:
        print(x + ", " + y + ": " + str(len(X[x][y])) + ", " + str(X[x][y][0]) + ", " + str(X[x][y][1]))

"""
*********************
"""
import matplotlib.pyplot as plt

fig, axs = plt.subplots(4)
fig.suptitle('Fun with a CAN bus')

def do(axs, i, data, label):
    axs[i].plot([x[0] for x in data], [x[1] for x in data], label=label)

def clean(axs, i, title):
    axs[i].set_title(title)
    axs[i].set_xlabel('time (s)')
    axs[i].legend()


do(axs, 0, X["07E3"]["2s2t"], "Pitch Input (degrees)")
do(axs, 0, X["0001"]["0f4"], "Pitch Angle (radians)")
do(axs, 0, X["0002"]["0f4"], "Pitch Rate (radians/s)")
clean(axs, 0, 'Pitch')

do(axs, 1, X["07E3"]["0s2t"], "Roll Input (degrees)")
do(axs, 1, X["0003"]["0f4"], "Roll Angle (radians)")
do(axs, 1, X["0004"]["0f4"], "Roll Rate (radians/s)")
clean(axs, 1, 'Roll')

do(axs, 2, X["07E3"]["4s2s"], "Yaw Input (degrees/s)")
do(axs, 2, X["0005"]["0f4"], "Yaw Angle (radians)")
do(axs, 2, X["0006"]["0f4"], "Yaw Rate (radians/s)")
clean(axs, 2, 'Yaw')

do(axs, 3, X["07E3"]["6u2"], "Hover Throttle")
do(axs, 3, X["07E4"]["2s2"], "Pusher Throttle")
do(axs, 3, X["07E4"]["0u1"], "Prop Spin")
clean(axs, 3, 'Hover')

plt.show()
