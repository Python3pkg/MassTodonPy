from aminoAcid import AminoAcid
from misc import plott
import igraph as ig
from collections import defaultdict, Counter

# def Protein(object):
# 	def __init__(fasta, bonds=[])

def aminosIter(fasta):
	aas 	= ('A','R','N','D','C','Q','E','G','H','I','L','K','M','F','P','S','T','W','Y','V')
	AAS 	= {}
	for aa in aas:
		AAS[aa] = AminoAcid(aa)
	for i,aa in enumerate(fasta):
		if i in (0, len(fasta)-1):
			A = AminoAcid(aa)
			if i == 0:
				A.add_H()
			if i == len(fasta)-1:
				A.add_OH()
		else:
			A = AAS[aa]
		yield ( A.getLeft(), A.getRight(), A.getGraph() )

def edges(fasta):
	prevElemNo = 0
	for left, right, G in aminosIter(fasta):
		for e in G.es:
			a, b = e.tuple 
			yield ( a+prevElemNo, b+prevElemNo ) # bonds within new AA
		if prevElemNo:
			yield ( prevElemNo+left, prevRight ) # bond between last AA and new AA
		prevRight 	= right + prevElemNo
		prevElemNo += len(G.vs)

def BondTypes(bonds = ['cz']):
	B2atoms = {	'cz': [ ('Nalpha', 'Calpha'), ('N1', 'C2') ],
				'by': [ ('Nalpha', 'Ccarbo'), ('N1', 'Ccarbo') ],
				'ax': [ ('Calpha','Ccarbo'), ('C2', 'Ccarbo') ]  	}
	B2B = defaultdict(lambda: None)
	try: 
		for b in bonds:
			for s,t in B2atoms[b]:	
				B2B[(s,t)] = B2B[(t,s)] = b
		return B2B
	except KeyError:
		print 'This type of bond is yet not considered: '+str(b)

def GetBonds(fasta, B2B):
	bondTypes= set(B2B[k] for k in B2B)
	notFirst = False
	for left, right, G in aminosIter(fasta):
		for e in G.es:
			yield B2B[ tuple(vName for vName in G.vs[e.tuple]['name']) ]
		if notFirst:
			if 'by' in bondTypes:
				yield 'by'
			else:
				yield None			
		else:	
			notFirst = True

def propGen(propName, fasta):
	if propName == 'name':
		return ( str(aaNo) + ':' + pN for aaNo, (_,_,G) in enumerate( aminosIter(fasta)) for pN in G.vs[propName] )
	else:
		return ( pN for _,_,G in aminosIter(fasta) for pN in G.vs[propName] )

def makeProtein( fasta, attributeNames=('name', 'elem'), bonds=['cz','ax','by'] ):
	N 	= sum( len(G.vs) for l,r,G in aminosIter(fasta) )
	B2B = BondTypes(bonds)
	G 	= ig.Graph(N)
	G.add_edges( edges(fasta) )
	for name in attributeNames:
		G.vs[name] = [ a for a in propGen(name, fasta) ]
	G.es['Roep'] = list(GetBonds(fasta,B2B))
	return G

def elementContent(G):
	atomNo = Counter()	
	for el in G.vs['elem']:
		atomNo[el] += 1
	return atomNo

substanceP 	= 'RPKPQQFFGLM'
ubiquitin 	= 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG'

fasta 	= ubiquitin
G 		= makeProtein(fasta,bonds=['cz'])		

E = G.copy()
E.delete_edges( i for i,bond in enumerate(E.es['Roep']) if not bond == None )
SuperAtoms = E.decompose()


	# This can be reduced in future
VerticesDivision = {}
for i, sA in enumerate(SuperAtoms):
	for vName in sA.vs['name']:
		VerticesDivision[vName] = i

startVertexIdx 	= G.vs.find('0:Ccarbo').index
SA_E = []
SA_E_att = defaultdict(list)
for v,_,parent in G.bfsiter( vid=startVertexIdx, mode='ALL', advanced=True ):
	if parent:
		bondType = G.es[G.get_eid( v.index, parent.index )]['Roep']
		if bondType:
			vFragNo = VerticesDivision[ v['name'] ] 
			pFragNo = VerticesDivision[ parent['name'] ] 
			if not vFragNo==pFragNo:
				SA_E.append( (pFragNo,vFragNo) )
				SA_E_att['Roep'].append( bondType )

SA_V_att = defaultdict(list)
SA_V_att['elementContent'] = [ elementContent(F) for F in SuperAtoms ]

SuperAtomsGraph = ig.Graph( 
	n 			= len(SuperAtoms), 
	edges 		= SA_E, 
	edge_attrs 	= SA_E_att,
	vertex_attrs= SA_V_att )




ig.plot( SuperAtomsGraph, bbox=(2000,1000), edge_label=SA_E_att['Roep'] )
plott(E, bbox=(20000,10000), target='/Volumes/doom/Users/matteo/Dropbox/Science/MassSpectrometry/MassTodon/Visual/ubiquitin2.pdf')


# layout = E.layout_lgl()
plott(E, bbox=(20000,10000), layout=layout, target='/Volumes/doom/Users/matteo/Dropbox/Science/MassSpectrometry/MassTodon/Visual/ubiquitin2.pdf')

# G 		= makeProtein(fasta, bonds=['cz','by','ax'])		
# layout 	= G.layout_lgl()
# plott(G, edge_label=G.es['Roep'], bbox=(20000,10000), layout=layout, target='/Volumes/doom/Users/matteo/Dropbox/Science/MassSpectrometry/MassTodon/Visual/ubiquitin.pdf')


# ends, __,starts = G.bfs(0)

