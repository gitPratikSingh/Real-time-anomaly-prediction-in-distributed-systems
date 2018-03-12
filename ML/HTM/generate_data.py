import csv
import math

ROWS = 5000

def run():
	fileHandle = open("sine.csv", "w")
	writer = csv.writer(fileHandle)
	writer.writerow(["angle", "sine"])
	writer.writerow(["float", "float"])
	writer.writerow(["",""])

	for i in range(ROWS):
		angle = (i*math.pi)/50.0
		sine_val = math.sin(angle)
		writer.writerow([angle, sine_val])

	fileHandle.close()

if __name__ == "__main__":
	run()


