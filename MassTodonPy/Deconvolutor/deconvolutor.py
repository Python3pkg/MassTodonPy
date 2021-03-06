# -*- coding: utf-8 -*-
#
#   Copyright (C) 2016 Mateusz Krzysztof Łącki and Michał Startek.
#
#   This file is part of MassTodon.
#
#   MassTodon is free software: you can redistribute it and/or modify
#   it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
#   Version 3.
#
#   MassTodon is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#   You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#   Version 3 along with MassTodon.  If not, see
#   <https://www.gnu.org/licenses/agpl-3.0.en.html>.

from    math        import sqrt
from    collections import Counter
from    cvxopt      import matrix, spmatrix, sparse, spdiag, solvers
solvers.options['show_progress'] = False


def diag(val, dim):
    return spdiag([spmatrix(val,[0],[0]) for i in range(dim)])


def normalize_rows(M):
    '''Divide rows of a matrix by their sums.'''
    for i in range(M.size[0]):
        row_hopefully = M[i,:]
        M[i,:] = row_hopefully/sum(row_hopefully)


def number_graph(SFG):
    '''Add numbers to graph nodes and GI edges and return the counts thereof.'''
    cnts = Counter()
    for N in SFG: # ordering some of the SFG graph nodes and edges
        Ntype = SFG.node[N]['type']
        SFG.node[N]['cnt'] = cnts[Ntype]
        cnts[Ntype] += 1
        if Ntype == 'G':
            for I in SFG.edge[N]:
                SFG.edge[N][I]['cnt'] = cnts['GI']
                cnts['GI'] += 1
    return cnts


def get_P_q( SFG, M_No, var_No, mu=0.0, lam=0.0, nu=0.0 ):
    '''Prepare cost function 0.5 <x|P|x> + <q|x> + mu * sum|alpha_m| + lam * sum |x_i|.'''
    q_list = []
    P_list = []
    for G_name in SFG:
        if SFG.node[G_name]['type']=='G':
            G_intensity = SFG.node[G_name]['intensity']
            G_degree    = len(SFG[G_name])
            q_list.append( matrix( -G_intensity, size=(G_degree,1)) )
            ones = matrix(1.0, (G_degree,1))
            P_g  = ones * ones.T + diag(lam,G_degree)
            P_list.append(P_g)
    q_list.append(matrix(nu, (M_No,1))) # L1 penalty for alphas
    q_vec = matrix(q_list)
    P_list.append(diag(mu, M_No))
    P_mat = spdiag(P_list)
    return P_mat, q_vec


def get_initvals(var_No):
    '''Initial values of flows.'''
    initvals= {}
    initvals['x'] = matrix( 0.0, (var_No, 1)  )
    return initvals


def get_G_h(var_No):
    '''Prepare for conditions Gx <= h'''
    G_mat = diag(-1.0, var_No)
    h_vec = matrix(0.0, size=(var_No, 1))
    return G_mat, h_vec


def get_A_b(SFG, M_No, I_No, GI_No):
    '''Prepare for conditions Ax = b'''
    A_x=[]; A_i=[]; A_j=[]
    for M in SFG:
        if SFG.node[M]['type']=='M':
            M_cnt = SFG.node[M]['cnt']
            for I in SFG[M]:
                i_cnt = SFG.node[I]['cnt']
                A_x.append(-SFG.node[I]['intensity'])# probability
                A_i.append( i_cnt )
                A_j.append( M_cnt + GI_No )
                for G in SFG[I]:
                    if not G == M:
                        A_x.append( 1.0 )
                        A_i.append( i_cnt )
                        A_j.append( SFG.edge[G][I]['cnt'] )
    A_mat = spmatrix( A_x, A_i, A_j, size=(I_No, M_No+GI_No ) )
    normalize_rows(A_mat)
    b_vec = matrix( 0.0, (I_No, 1)  )
    return A_mat, b_vec


class Deconvolutor(object):
    '''Class for deconvolving individual Small Graphs.'''
    def __init__(self, SFG):
        self.SFG = SFG
        cnts = number_graph(self.SFG)
        self.set_names(cnts)

    def set_names(self, cnts):
        self.var_No = cnts['GI'] + cnts['M']
        self.M_No   = cnts['M']
        self.GI_No  = cnts['GI']
        self.I_No   = cnts['I']
        self.G_No   = cnts['G']

    def run(self, **args):
        '''Perform deconvolution.'''
        raise NotImplementedError

    def get_mean_square_error(self):
        error = 0.0
        for G_name in self.SFG:
            if self.SFG.node[G_name]['type'] == 'G':
                I_intensity = self.SFG.node[G_name]['intensity']
                outflow = 0.0
                for I_name in self.SFG[G_name]:
                    GI = self.SFG.edge[G_name][I_name]
                    outflow += self.sol['x'][GI['cnt']]
                error += (I_intensity - outflow)**2
        error = sqrt(error)
        return error

class Deconvolutor_Min_Sum_Squares(Deconvolutor):
    def run(self, mu=1e-5, lam=0.0, nu=0.0, spectral_norm=False):
        '''Perform deconvolution that minimizes the mean square error.'''

        P, q = get_P_q(self.SFG, self.M_No, self.var_No, mu, lam, nu)
        x0   = get_initvals(self.var_No)
        G, h = get_G_h(self.var_No)
        A, b = get_A_b(self.SFG, self.M_No, self.I_No, self.GI_No)
        self.sol  = solvers.qp(P, q, G, h, A, b, initvals=x0)
        Xopt = self.sol['x']
        #################### reporting results
        alphas = []
        for N_name in self.SFG:
            N = self.SFG.node[N_name]
            if N['type'] == 'M':
                N['estimate'] = Xopt[self.GI_No + N['cnt']]
                alphas.append(N.copy())
            if N['type'] == 'G':
                for I_name in self.SFG[N_name]:
                    NI = self.SFG.edge[N_name][I_name]
                    NI['estimate'] = Xopt[NI['cnt']]
        error = self.get_mean_square_error()
        return alphas, error, self.sol['status']

class Deconvolutor_Max_Flow(Deconvolutor):
    def set_names(self, cnts):
        self.var_No = cnts['GI'] + cnts['M'] + + cnts['G']
        self.M_No   = cnts['M']
        self.GI_No  = cnts['GI']
        self.I_No   = cnts['I']
        self.G_No   = cnts['G']

    def run(self, lam=10.0, mu=0.0, eps=0.0, s0_val=0.001):
        G_tmp, h_tmp = get_G_h(self.var_No)
        h_eps = matrix(0.0, (self.G_No,1))
        G_x=[]; G_i=[]; G_j=[]
        for G_name in self.SFG:
            G = self.SFG.node[G_name]
            if G['type'] == 'G':
                g_cnt = G['cnt']
                h_eps[g_cnt] = G['intensity'] + eps
                for I_name in self.SFG[G_name]:
                    i_cnt = self.SFG.node[I_name]['cnt']
                    G_x.append(1.0)
                    G_i.append(g_cnt)
                    G_j.append(i_cnt)
                G_x.append(-1.0)
                G_i.append(g_cnt)
                G_j.append(self.GI_No + self.M_No + g_cnt)
        G_tmp2 = spmatrix( G_x, G_i, G_j, size=( self.G_No, self.var_No ) )
        G = sparse([G_tmp, G_tmp2])
        h = matrix([h_tmp, h_eps])

        A_tmp, b = get_A_b(self.SFG, self.M_No, self.I_No, self.GI_No)
        A_eps = spmatrix([],[],[], (self.I_No, self.G_No))
        A = sparse([[A_tmp],[A_eps]])

        x0 = get_initvals(self.var_No)
        x0['s'] = matrix(s0_val, size=h.size)

        c = matrix([
                matrix( -1.0,       size=(self.GI_No,1) ),
                matrix( mu,         size=(self.M_No,1)  ),
                matrix( (1.0+lam),  size=(self.G_No,1)  )   ])

        self.sol = solvers.conelp(c=c,G=G,h=h,A=A,b=b,primalstart=x0)
        Xopt = self.sol['x']

        alphas = [] # reporting results
        for N_name in self.SFG:
            N = self.SFG.node[N_name]
            if N['type'] == 'M':
                N['estimate'] = Xopt[self.GI_No + N['cnt']]
                alphas.append(N.copy())
            if N['type'] == 'G':
                for I_name in self.SFG[N_name]:
                    NI = self.SFG.edge[N_name][I_name]
                    NI['estimate'] = Xopt[NI['cnt']]
                    g_cnt = self.GI_No + self.M_No + N['cnt']
                    N['relaxation'] = Xopt[g_cnt]

        # fit error: evaluation of the cost function at the minimizer
        error = self.get_mean_square_error()

        return alphas, error, self.sol['status']


def deconvolve(SFG, args, method):
    deconvolutor = {
        'MSE':      Deconvolutor_Min_Sum_Squares,
        'MaxFlow':  Deconvolutor_Max_Flow
    }[method](SFG)
    alphas, error, status = deconvolutor.run(**args)
    return alphas, error, status
