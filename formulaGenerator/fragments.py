import numpy  as np
import itertools as it
from collections import Counter
from aminoAcid import AminoAcids
try:
  import cPickle as pickle
except:
  import pickle


ubiquitin = 'MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG'
substanceP= 'RPKPQQFFGLM'

def elementContent(G):
    '''Extracts numbes of atoms of elements that make up the graph of a molecule.'''
    atomNo = Counter()
    for el in G.vs['elem']:
        atomNo[el] += 1
    return atomNo


def fasta2atomCount(fasta):
    '''Represents a fasta sequence, or a list of fasta sequences, as an atom count of the underlying protein. Returns a dictionary of atom counts.'''
    if isinstance(fasta, str):
        fasta = [fasta]
    AA = AminoAcids()
    assert AA.are_encoded(fasta), 'Fuck'
    aminoAcids = AA.get()
    result = {}
    for f in fasta:
        atomCnt = Counter()
        aminoAcidCounts = Counter(f)
        for aa in aminoAcidCounts:
            atomCnt_of_aa = elementContent( aminoAcids[aa]['graph'] )
            for atom in atomCnt_of_aa:
                atomCnt[atom] += atomCnt_of_aa[atom]*aminoAcidCounts[aa]
        # Adding water.
        atomCnt['H'] += 2
        atomCnt['O'] += 1
        result[f] = atomCnt
    return result

fasta = ['RPKPQQFFGLM','MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG']
ubiquitin,substanceP = fasta
# fasta2atomCount(fasta)
# fasta2atomCount('A')

def getAminoAcids():
    aas = ('A','R','N','D','C','Q','E','G','H','I','L','K','M','F','P','S','T','W','Y','V')
    aminoAcids = {}
    for aa in aas:
        AA = AminoAcid(aa)
        aminoAcids[aa] ={ 'graph' : AA.getGraph(), 'NalphaIDX' : AA.Nalpha(), 'CcarboIDX' : AA.Ccarbo() }
    return aminoAcids


# def simplifyAminoAcid(aaTag, bonds2break = ('cz',)):
#       '''Differentiates between precisely enumerated modifications and others.'''
#     if isinstance( bonds2break, type(tuple()) ):
#         pass
#     elif isinstance( bonds2break, type(dict()) ):
#         pass
#     else:
#         print('Unrecognizable format of bonds to break.')
#         pass

def establishFragmentType(fragment, aaType):
    '''Establishes what is the fragment type: (L)eft, (C)enter, or (R)ight, or (LC) or (R) for proline.

        L fragment is a fictitious double fragmentation product of b-y and c-z cleavages,
        C - of c-z and a-x cleavages,
        R - of a-x and b-y cleavages.
    '''
    if aaType == 'P':
        if 'Ccarbo' in fragment.vs['name']:
            return 'R'
        else:
            return 'LC'
    else:
        if 'Calpha' in fragment.vs['name']:
            return 'C'
        elif 'Nalpha' in fragment.vs['name']:
            return 'L'
        else:
            return 'R'


def getSuperAtoms(fasta, fragmentTypes):
    '''Enlists all fictitious double fragmentation products.

    These are all basic chemical formulas obtainable in double fragmentation.'''
    fragments = {}
    aminoAcids= getAminoAcids()
    for f in set(fasta):
        G = aminoAcids[f]['graph'].copy()
        G.delete_edges(Roep_ne=None)
        G = G.decompose()
        G = dict( (establishFragmentType(g,f), elementContent(g)) for g in G )
        if set(G) == set(['L','C','R']):
            if 'ax' in fragmentTypes:
                if 'cz' in fragmentTypes:
                    G = [ ('LL', G['L']), ('CC',G['C']), ('RR',G['R']) ]
                else:
                    G = [ ('LC', G['L']+G['C']), ('RR', G['R']) ]
            else:
                if 'cz' in fragmentTypes:
                    G = [ ('LL', G['L']), ('CR', G['C']+G['R']) ]
                else:
                    G = [ ('LR', G['L']+G['C']+G['R']) ]
        elif set(G) == set(['LC','R']):
            if 'ax' in fragmentTypes:
                G = [ ('LC', G['LC']), ('RR', G['R']) ]
            else:
                G = [ ('LR', G['LC']+G['R']) ]
        else:
            print('It is impossible to get here, but you did it. Immediately go to a casino, as this is your lucky day.')
        fragments[f] = G
    #
    superAtoms = [] # It must be a list to be mutable.
    for fNo, f in enumerate(fasta):
        if fNo==0 or 'by' in fragmentTypes:
            for aaType, atomCnt in fragments[f]:
                superAtoms.append([ aaType, fNo, fNo, atomCnt.copy() ])
        else:
            for fragNo, fragment in enumerate(fragments[f]):
                aaType, atomCnt = fragment
                if fragNo==0:
                    # [ aaType, fNo, fNo, Counter() ]
                    superAtoms[-1][-1].update(atomCnt)
                    # Update left right fragment tags.
                    superAtoms[-1][0] = superAtoms[-1][0][0] + aaType[-1]
                    # Upadate second fragment tag counter.
                    superAtoms[-1][2] = fNo
                else:
                    superAtoms.append([ aaType, fNo, fNo, atomCnt.copy() ])
    #
    # Adding water to the molecule: acids' backbones were water free
    superAtoms[0][-1]['H']  += 1
    superAtoms[-1][-1]['H'] += 1
    superAtoms[-1][-1]['O'] += 1
    #
    assert any( sA[1]<=sA[2] for sA in superAtoms )
    return superAtoms


def makeFragments(fasta, fragmentTypes=['cz'], innerFragments = False):
    '''Makes tagged chemical formulas of fragments under given fragmentation scheme.

    The tags contain information the cleavage sites: the left and/or right endings.
    '''
    fragmentTypes   = set(fragmentTypes)
    superAtoms      = getSuperAtoms(fasta, fragmentTypes)
    fragments = []
    if innerFragments:
        for i in range(len(superAtoms)):
            fragments.append(superAtoms[i])
            for j in range(i+1,len(superAtoms)):
                SA1     = fragments[-1]
                SA2     = superAtoms[j]
                aaType  = SA1[0][0]+SA2[0][1]
                lFragNo = SA1[1]
                rFragNo = SA2[2]
                atomCnt = SA1[3]+SA2[3]
                fragments.append([aaType, lFragNo, rFragNo, atomCnt])
    else:
        prevCnt = Counter()
        # abc fragments--------------------------------------------------
        for aaType, lFragNo, rFragNo, atomCnt in superAtoms:
            isCfragment = aaType[1] == 'L'
            aaType  = 'L'+aaType[-1]
            lFragNo = 0
            prevCnt = prevCnt + atomCnt
            if isCfragment:
                atomCnt = prevCnt + Counter({'H':1})
            else:
                atomCnt = prevCnt
            fragments.append([aaType, lFragNo, rFragNo, atomCnt])
        #----------------------------------------------------------------
        precursor1  = fragments[-1]
        prevCnt     = Counter()
        superAtoms.reverse()
        L = len(fasta)
        # xyz fragments--------------------------------------------------
        for aaType, lFragNo, rFragNo, atomCnt in superAtoms:
            aaType  = aaType[0]+'R'
            rFragNo = L-1
            prevCnt = prevCnt + atomCnt
            fragments.append([aaType, lFragNo, rFragNo, prevCnt])
        #----------------------------------------------------------------
        precursor2  = fragments[-1]
        assert precursor1==precursor2
        # Removin extra precursor---------------------------------------
        del fragments[-1]
    return fragments



def roepstorffy(fragment,fasta):
    '''Sprinkle my naming convention with Roepstorff's pseudo-scientific naming.'''
    L = len(fasta)
    AAtype, AAleft, AAright, atomCnt = fragment
    lType, rType = AAtype
    lcr2abc = {'L':'c','C':'a','R':'b'}
    lcr2xyz = {'L':'y','C':'z','R':'x'}
    if lType=='L' and AAleft==0:
        nameL = ''
    else:
        lType = lcr2xyz[lType]
        nameL = lType + str(L-AAleft-(1 if lType=='x' else 0))
        # lType + str(L-AAleft+1+(0 if lType=='x' else 1))
    if rType=='R' and AAright==L-1:
        nameR = ''
    else:
        rType = lcr2abc[rType]
        nameR = rType + str(AAright+1-(1 if rType=='c' else 0))
    name = nameL+nameR
    if name=='':
        return 'precursor'
    else:
        return name



ubiFrags = makeFragments(ubiquitin)
subPfrags= makeFragments(substanceP)
ubiRoep  = [ roepstorffy(x,ubiquitin) for x in ubiFrags ]
subProep = [ roepstorffy(x,substanceP) for x in subPfrags ]

with open('/Users/matteo/Documents/MassTodon/MassTodonPy/formulaGenerator/ATOMCNTS.data', 'w') as f:
    pickle.dump( { 'ubiFrags': ubiFrags, 'subPfrags':subPfrags, 'ubiRoep':ubiRoep, 'subProep':subProep }, f )

def sideChainsNo(fragment):
    '''Finds the number of side chains on a fragment.'''
    pos, leftAA, rightAA, _ = fragment
    leftPos, rightPos       = pos
    res = rightAA - leftAA + 1
    if leftPos == 'R':
        res -= 1
    if rightPos== 'L':
        res -= 1
    if res < 0:
        res = 0
    return res


def getProtonation(max_q, max_q_on_fragment):
    '''Enumerated protonation and quenched protonation numbers.'''
    for q in range(1, max_q_on_fragment):
        for g in range(max_q-q):
            yield (q,g)

list( getProtonation(10,9) )


def protonatedFragments(    fasta,
                            max_charge,
                            amino_acids_per_charge  = 5,
                            fragmentTypes           = ['cz'],
                            innerFragments          = False     ):
    fragments = makeFragments(fasta, fragmentTypes, innerFragments)
    for fragment in fragments:
        maxQonFrag = round(sideChainsNo(fragment)/float(amino_acids_per_charge))
        for q,g in getProtonation( max_charge, maxQonFrag ):
            yield (q,g, fragment)

# res = list( protonatedFragments( ubiquitin, 20) )
# len(res)
