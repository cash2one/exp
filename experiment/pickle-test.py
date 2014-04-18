import StringIO
import pickle

f = StringIO.StringIO()
x = ['a', '<html></html>']
pickle.dump(x, f)
value = f.getvalue()

# read it back
x = pickle.loads(value)
print x
print x[0]
print x[1]
