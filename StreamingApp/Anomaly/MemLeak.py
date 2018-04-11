
def memLeak():
	# takes up memory exponentially
	# adds 1 KB, 2KB, 4kB and so on
	a = []
	i = 0
	while True:
		print len(a)
		a.append(' ' * (2**i))
		i = i+1
	
if __name__ == "__main__":
    memLeak()
