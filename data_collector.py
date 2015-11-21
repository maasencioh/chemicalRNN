from chemspipy import ChemSpider

# user key
cs = ChemSpider('06ac2655-ee0a-4c26-87dd-3f64b42399b3')

# range values
begin = 0
end = 35000000
for i in xrange(begin, end):
    try:
        # chemspider object
        c = cs.get_compound(i)
        name = c.common_name
        smiles = c.smiles
        print i,';',name,';',smiles
    except Exception as e:
        pass
