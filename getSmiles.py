import random

f = open("data.csv")
s1 = open("ptb.train.txt", "w")
s2 = open("ptb.test.txt", "w")
s3 = open("ptb.valid.txt", "w")

lines = f.readlines()

print len(lines)

random.shuffle(lines)

for i in xrange(int(len(lines) * 0.6)):
    s1.write(" | " + " ".join(lines[i].split(";")[-1].replace(" ", "").replace("_", "!")))

for i in xrange(int(len(lines) * 0.6), int(len(lines) * 0.8)):
    s2.write(" | " + " ".join(lines[i].split(";")[-1].replace(" ", "").replace("_", "!")))

for i in xrange(int(len(lines) * 0.8), len(lines)):
    s3.write(" | " + " ".join(lines[i].split(";")[-1].replace(" ", "").replace("_", "!")))

s1.close()
s2.close()
s3.close()
f.close()