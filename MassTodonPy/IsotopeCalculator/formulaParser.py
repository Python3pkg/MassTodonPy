import re
from collections import Counter

class formulaParser(object):
    def __init__(self, pattern = '([A-Z][a-z]?)([0-9]*)' ):
        self.elementTags = {"O","Xe","Cs","Hg","S","Ru","H","Zn","Sr","Al","Sm","Zr","Ho","Ta","Pb","Te","He","Ti","As","Ge","Pr","U","Tl","Ir","Tm","Fe","Si","Cl","Eu","Tb","W","Er","P","Os","K","Dy","Lu","Bi","Ga","Pt","La","Be","F","Yb","Kr","Cd","Mn","Ar","Cr","Se","Sb","Hf","Sc","Ca","Ba","Rb","Sn","Co","Cu","Ne","Pd","In","N","Au","Y","Ni","Rh","C","Li","Th","B","Mg","Na","Pa","V","Re","Nd","Br","Ce","I","Ag","Gd","Nb","Mo"}
        self.pattern = re.compile(pattern)

    def parse(self, atomCnt_str):
        """Parses chemical formula based on the pattern definition."""
        atomCnt = Counter()
        for elemTag, cnt  in re.findall(self.pattern, atomCnt_str) :
            if elemTag in self.elementTags:
                if cnt == '':
                    cnt = 1
                else:
                    cnt = int(cnt)
                atomCnt[elemTag] += cnt
            else:
                raise AttributeError;
        return atomCnt
